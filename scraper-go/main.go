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
	client      *http.Client
	semaphore   *semaphore.Weighted
	config      ParserConfig
	validator   *Validator
	broker      MessageBroker
	coordinator *EtcdCoordinator
	aggregator  *Aggregator
}

// NewNewsScraper creates a new scraper instance
func NewNewsScraper(config ParserConfig) *NewsScraper {
	validator := NewValidator(config.EnableValidation)
	
	var broker MessageBroker
	if config.Broker.Enabled {
		var err error
		broker, err = BrokerFactory(config.Broker)
		if err != nil {
			log.Printf("Warning: Failed to create broker: %v", err)
			log.Println("Continuing without broker...")
		} else {
			if err := broker.Connect(); err != nil {
				log.Printf("Warning: Failed to connect to broker: %v", err)
				log.Println("Continuing without broker...")
				broker = nil
			} else {
				log.Printf("Connected to %s broker", config.Broker.Type)
			}
		}
	}
	
	var coordinator *EtcdCoordinator
	if config.Etcd.Enabled {
		var err error
		coordinator, err = NewEtcdCoordinator(config.Etcd)
		if err != nil {
			log.Printf("Warning: Failed to create etcd coordinator: %v", err)
			log.Println("Continuing without etcd coordination...")
		} else {
			log.Println("Connected to etcd for distributed coordination")
			
			// Register sources in etcd
			if err := registerSourcesInEtcd(coordinator); err != nil {
				log.Printf("Warning: Failed to register sources in etcd: %v", err)
			}
		}
	}
	
	var aggregator *Aggregator
	if config.Aggregation.Enabled {
		aggregator = NewAggregator(config.Aggregation)
		log.Printf("Aggregation enabled: %s window, size %d", 
			config.Aggregation.WindowType, config.Aggregation.WindowSize)
		
		// Start monitoring aggregation flush channel
		go monitorAggregation(aggregator)
	}
	
	return &NewsScraper{
		client: &http.Client{
			Timeout: time.Duration(config.RequestTimeout) * time.Second,
		},
		semaphore:   semaphore.NewWeighted(int64(config.MaxConcurrentRequests)),
		config:      config,
		validator:   validator,
		broker:      broker,
		coordinator: coordinator,
		aggregator:  aggregator,
	}
}

// monitorAggregation monitors and logs aggregated statistics
func monitorAggregation(aggregator *Aggregator) {
	for stats := range aggregator.GetFlushChannel() {
		statsJSON, err := json.MarshalIndent(stats, "", "  ")
		if err != nil {
			log.Printf("Failed to marshal aggregation stats: %v", err)
			continue
		}
		
		log.Printf("Aggregation window statistics:\n%s", statsJSON)
		
		// TODO: Send to Apache Arrow Flight server (commit 17)
		// TODO: Send to broker for Python consumption
	}
}

// registerSourcesInEtcd registers all configured sources in etcd
func registerSourcesInEtcd(coordinator *EtcdCoordinator) error {
	for _, source := range RSSSources {
		config := map[string]interface{}{
			"name": source.Name,
			"type": source.Type,
			"url":  source.URL,
		}
		if err := coordinator.RegisterSource(source.URL, config); err != nil {
			return fmt.Errorf("failed to register source %s: %w", source.Name, err)
		}
	}
	log.Printf("Registered %d sources in etcd", len(RSSSources))
	return nil
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

// scrapeSourceWithLock scrapes a source with etcd locking
func (s *NewsScraper) scrapeSourceWithLock(ctx context.Context, source RSSSource) ([]Article, error) {
	if s.coordinator != nil {
		// Try to acquire lock with timeout
		locked, err := s.coordinator.AcquireSourceLock(source.URL, 10*time.Second)
		if err != nil {
			log.Printf("Error acquiring lock for %s: %v", source.Name, err)
			return nil, err
		}
		
		if !locked {
			log.Printf("Could not acquire lock for %s (may be locked by another worker)", source.Name)
			return nil, fmt.Errorf("source %s is locked by another worker", source.Name)
		}
		
		// Ensure lock is released
		defer func() {
			if err := s.coordinator.ReleaseSourceLock(source.URL); err != nil {
				log.Printf("Error releasing lock for %s: %v", source.Name, err)
			}
		}()
		
		log.Printf("Acquired lock for source: %s", source.Name)
	}
	
	// Scrape the source
	return s.scrapeSource(ctx, source)
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

// publishToBroker sends articles to message broker
func (s *NewsScraper) publishToBroker(articles []Article) error {
	if s.broker == nil || len(articles) == 0 {
		return nil
	}

	log.Printf("Publishing %d articles to %s broker", len(articles), s.config.Broker.Type)
	
	// Try batch publish first, fall back to individual
	err := s.broker.PublishBatch(articles)
	if err != nil {
		log.Printf("Batch publish failed, trying individual: %v", err)
		
		successCount := 0
		for i, article := range articles {
			if err := s.broker.Publish(&article); err != nil {
				log.Printf("Failed to publish article %d '%s': %v", i, article.Title, err)
			} else {
				successCount++
			}
		}
		
		log.Printf("Published %d/%d articles to broker", successCount, len(articles))
		if successCount == 0 {
			return fmt.Errorf("failed to publish any articles to broker")
		}
	} else {
		log.Printf("Successfully published %d articles to broker", len(articles))
	}
	
	return nil
}

// getSourcesToScrape returns sources to scrape based on coordination mode
func (s *NewsScraper) getSourcesToScrape() ([]RSSSource, error) {
	if s.coordinator != nil {
		// Get available sources from etcd
		availableURLs, err := s.coordinator.GetAvailableSources()
		if err != nil {
			log.Printf("Error getting available sources from etcd: %v", err)
			log.Println("Falling back to configured sources...")
			return RSSSources, nil
		}
		
		// Map URLs to RSSSource objects
		var sources []RSSSource
		for _, url := range availableURLs {
			for _, source := range RSSSources {
				if source.URL == url {
					sources = append(sources, source)
					break
				}
			}
		}
		
		log.Printf("Found %d available sources via etcd coordination", len(sources))
		return sources, nil
	}
	
	// No coordination, use all configured sources
	return RSSSources, nil
}

// Run starts the scraping process
func (s *NewsScraper) Run(ctx context.Context) error {
	log.Println("Starting concurrent news scraper")
	
	// Get sources to scrape (with coordination if enabled)
	sources, err := s.getSourcesToScrape()
	if err != nil {
		return fmt.Errorf("failed to get sources: %w", err)
	}
	
	if len(sources) == 0 {
		log.Println("No sources available for scraping")
		return nil
	}
	
	log.Printf("Scraping %d sources", len(sources))

	var wg sync.WaitGroup
	results := make(chan []Article, len(sources))
	errors := make(chan error, len(sources))

	// Launch goroutines for each source
	for _, source := range sources {
		wg.Add(1)
		go func(src RSSSource) {
			defer wg.Done()
			
			articles, err := s.scrapeSourceWithLock(ctx, src)
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
		
		// Add to aggregator if enabled
		if s.aggregator != nil {
			for _, article := range articles {
				s.aggregator.AddArticle(article)
			}
		}
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

	// Publish to broker if enabled
	if s.broker != nil && len(validatedArticles) > 0 {
		if err := s.publishToBroker(validatedArticles); err != nil {
			log.Printf("Warning: Failed to publish to broker: %v", err)
			log.Println("Falling back to JSON file storage...")
			// Fall back to JSON storage
			if err := s.saveToJSON(validatedArticles); err != nil {
				return fmt.Errorf("failed to save articles to JSON: %w", err)
			}
		} else {
			log.Println("Articles successfully published to broker")
			// Optionally also save to JSON for backup
			if s.config.OutputDir != "" {
				if err := s.saveToJSON(validatedArticles); err != nil {
					log.Printf("Warning: Failed to save backup to JSON: %v", err)
				}
			}
		}
	} else if len(validatedArticles) > 0 {
		// Save to JSON if no broker
		if err := s.saveToJSON(validatedArticles); err != nil {
			return fmt.Errorf("failed to save articles to JSON: %w", err)
		}
		log.Printf("Total collected %d articles (%d after validation)", 
			len(allArticles), len(validatedArticles))
	} else {
		log.Println("No articles collected")
	}

	return nil
}

// Close cleans up resources
func (s *NewsScraper) Close() error {
	var errors []error
	
	if s.broker != nil {
		if err := s.broker.Close(); err != nil {
			errors = append(errors, fmt.Errorf("broker close error: %w", err))
		}
	}
	
	if s.coordinator != nil {
		if err := s.coordinator.Close(); err != nil {
			errors = append(errors, fmt.Errorf("coordinator close error: %w", err))
		}
	}
	
	if s.aggregator != nil {
		s.aggregator.Stop()
	}
	
	if len(errors) > 0 {
		return fmt.Errorf("errors during close: %v", errors)
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
	
	// Create scraper instance
	scraper := NewNewsScraper(Config)
	defer scraper.Close()

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(Config.RequestTimeout+10)*time.Second)
	defer cancel()

	// Run scraper
	if err := scraper.Run(ctx); err != nil {
		log.Fatalf("Scraper failed: %v", err)
	}

	log.Println("Scraping completed successfully")
}