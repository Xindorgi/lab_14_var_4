package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/mmcdole/gofeed"
	"github.com/PuerkitoBio/goquery"
	"golang.org/x/sync/semaphore"
)

// Article represents a news article
type Article struct {
	Source        string    `json:"source"`
	SourceType    string    `json:"source_type"`
	Title         string    `json:"title"`
	Link          string    `json:"link"`
	Description   string    `json:"description"`
	Published     string    `json:"published"`
	PublishedTime time.Time `json:"published_time,omitempty"`
	Authors       []string  `json:"authors"`
	Categories    []string  `json:"categories"`
	ScrapedAt     time.Time `json:"scraped_at"`
}

// NewsScraper implements concurrent RSS/HTML scraper
type NewsScraper struct {
	client    *http.Client
	semaphore *semaphore.Weighted
	config    ParserConfig
	validator *Validator
}

// NewNewsScraper creates a new scraper instance
func NewNewsScraper(config ParserConfig, enableValidation bool) *NewsScraper {
	validator := NewValidator(enableValidation)
	
	return &NewsScraper{
		client: &http.Client{
			Timeout: time.Duration(config.RequestTimeout) * time.Second,
		},
		semaphore: semaphore.NewWeighted(int64(config.MaxConcurrentRequests)),
		config:    config,
		validator: validator,
	}
}

// fetchURL fetches content from a URL
func (s *NewsScraper) fetchURL(ctx context.Context, url string) (string, error) {
	if err := s.semaphore.Acquire(ctx, 1); err != nil {
		return "", fmt.Errorf("failed to acquire semaphore: %w", err)
	}
	defer s.semaphore.Release(1)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("User-Agent", s.config.UserAgent)

	resp, err := s.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to fetch URL: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("non-200 status code: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response body: %w", err)
	}

	return string(body), nil
}

// parseRSS parses RSS feed
func (s *NewsScraper) parseRSS(ctx context.Context, source RSSSource) ([]Article, error) {
	log.Printf("Parsing RSS: %s", source.Name)

	content, err := s.fetchURL(ctx, source.URL)
	if err != nil {
		log.Printf("Error fetching RSS %s: %v", source.Name, err)
		return nil, err
	}

	fp := gofeed.NewParser()
	feed, err := fp.ParseString(content)
	if err != nil {
		log.Printf("Error parsing RSS %s: %v", source.Name, err)
		return nil, err
	}

	var articles []Article
	for _, item := range feed.Items {
		var authors []string
		for _, author := range item.Authors {
			authors = append(authors, author.Name)
		}

		var categories []string
		for _, category := range item.Categories {
			categories = append(categories, category)
		}

		article := Article{
			Source:      source.Name,
			SourceType:  "rss",
			Title:       item.Title,
			Link:        item.Link,
			Description: item.Description,
			Published:   item.Published,
			Authors:     authors,
			Categories:  categories,
			ScrapedAt:   time.Now().UTC(),
		}

		if item.PublishedParsed != nil {
			article.PublishedTime = *item.PublishedParsed
		}

		articles = append(articles, article)
	}

	log.Printf("Found %d articles in %s", len(articles), source.Name)
	return articles, nil
}

// parseHTML parses HTML page (example for BBC Russian)
func (s *NewsScraper) parseHTML(ctx context.Context, source RSSSource) ([]Article, error) {
	log.Printf("Parsing HTML: %s", source.Name)

	content, err := s.fetchURL(ctx, source.URL)
	if err != nil {
		log.Printf("Error fetching HTML %s: %v", source.Name, err)
		return nil, err
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(content))
	if err != nil {
		log.Printf("Error parsing HTML %s: %v", source.Name, err)
		return nil, err
	}

	var articles []Article
	// Simplified parsing for demonstration
	// This would need to be adapted for specific website structure
	doc.Find("article, div[class*='promo'], div[class*='news']").Each(func(i int, sel *goquery.Selection) {
		// Limit to 10 articles for demonstration
		if i >= 10 {
			return
		}

		title := sel.Find("h1, h2, h3, h4, a[class*='heading']").First().Text()
		link, _ := sel.Find("a").First().Attr("href")

		if title != "" && link != "" {
			// Convert relative URLs to absolute
			if strings.HasPrefix(link, "/") {
				link = "https://www.bbc.com" + link
			}

			article := Article{
				Source:     source.Name,
				SourceType: "html",
				Title:      strings.TrimSpace(title),
				Link:       link,
				ScrapedAt:  time.Now().UTC(),
			}
			articles = append(articles, article)
		}
	})

	log.Printf("Found %d articles in %s (HTML)", len(articles), source.Name)
	return articles, nil
}

// scrapeSource scrapes a single source
func (s *NewsScraper) scrapeSource(ctx context.Context, source RSSSource) ([]Article, error) {
	switch source.Type {
	case "rss":
		return s.parseRSS(ctx, source)
	case "html":
		return s.parseHTML(ctx, source)
	default:
		log.Printf("Unknown source type: %s", source.Type)
		return nil, fmt.Errorf("unknown source type: %s", source.Type)
	}
}

// saveToJSON saves articles to JSON file
func (s *NewsScraper) saveToJSON(articles []Article) error {
	// Create output directory if it doesn't exist
	if err := os.MkdirAll(s.config.OutputDir, 0755); err != nil {
		return fmt.Errorf("failed to create output directory: %w", err)
	}

	outputPath := filepath.Join(s.config.OutputDir, s.config.OutputFilename)

	// Read existing data if file exists
	var existingData []Article
	if _, err := os.Stat(outputPath); err == nil {
		file, err := os.Open(outputPath)
		if err == nil {
			defer file.Close()
			if err := json.NewDecoder(file).Decode(&existingData); err != nil {
				log.Printf("Warning: failed to decode existing JSON: %v", err)
			}
		}
	}

	// Append new articles
	existingData = append(existingData, articles...)

	// Write updated data
	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create output file: %w", err)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(existingData); err != nil {
		return fmt.Errorf("failed to encode JSON: %w", err)
	}

	log.Printf("Saved %d articles to %s", len(articles), outputPath)
	return nil
}

// Run starts the scraping process
func (s *NewsScraper) Run(ctx context.Context) error {
	log.Println("Starting concurrent news scraper")

	var wg sync.WaitGroup
	results := make(chan []Article, len(RSSSources))
	errors := make(chan error, len(RSSSources))

	// Launch goroutines for each source
	for _, source := range RSSSources {
		wg.Add(1)
		go func(src RSSSource) {
			defer wg.Done()
			
			articles, err := s.scrapeSource(ctx, src)
			if err != nil {
				errors <- fmt.Errorf("error scraping %s: %w", src.Name, err)
				return
			}
			results <- articles
		}(source)
	}

	// Wait for all goroutines to complete
	wg.Wait()
	close(results)
	close(errors)

	// Collect results
	var allArticles []Article
	for articles := range results {
		allArticles = append(allArticles, articles...)
	}

	// Check for errors
	var scrapeErrors []error
	for err := range errors {
		scrapeErrors = append(scrapeErrors, err)
	}

	if len(scrapeErrors) > 0 {
		log.Printf("Encountered %d errors during scraping", len(scrapeErrors))
		for _, err := range scrapeErrors {
			log.Printf("Scraping error: %v", err)
		}
	}

	// Validate articles if validator is enabled
	var validatedArticles []Article
	if s.validator != nil && len(allArticles) > 0 {
		log.Println("Starting article validation...")
		validated, validationErrors := s.validator.ValidateArticles(allArticles)
		
		if len(validationErrors) > 0 {
			log.Printf("Validation errors: %d articles failed validation", len(validationErrors))
			for _, err := range validationErrors {
				log.Printf("Validation error: %v", err)
			}
		}
		
		validatedArticles = validated
		log.Printf("Validation complete: %d articles valid, %d failed", 
			len(validated), len(allArticles)-len(validated))
	} else {
		validatedArticles = allArticles
	}

	// Save results if we have any articles
	if len(validatedArticles) > 0 {
		if err := s.saveToJSON(validatedArticles); err != nil {
			return fmt.Errorf("failed to save articles: %w", err)
		}
		log.Printf("Total collected %d articles (%d after validation)", 
			len(allArticles), len(validatedArticles))
	} else {
		log.Println("No articles collected")
	}

	return nil
}

func main() {
	// Set up logging
	log.SetFlags(0)
	log.SetOutput(os.Stdout)

	// Check if validator can be built
	if err := BuildValidator(); err != nil {
		log.Printf("Warning: Validator initialization failed: %v", err)
		log.Println("Continuing without validation...")
	}
	
	// Enable validation by default (can be made configurable)
	enableValidation := true

	// Create scraper instance
	scraper := NewNewsScraper(Config, enableValidation)

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(Config.RequestTimeout+10)*time.Second)
	defer cancel()

	// Run scraper
	if err := scraper.Run(ctx); err != nil {
		log.Fatalf("Scraper failed: %v", err)
	}

	log.Println("Scraping completed successfully")
}