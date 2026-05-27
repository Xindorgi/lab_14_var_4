package main

import (
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"
)

// AggregationConfig contains aggregation configuration
type AggregationConfig struct {
	Enabled          bool
	WindowType       string // "time" or "count"
	WindowSize       int    // seconds for time window, count for count window
	MaxWindowSize    int    // maximum articles per window before forced flush
	AggregationTypes []string // types of aggregations to compute
}

// AggregatedStats represents aggregated statistics for a window
type AggregatedStats struct {
	WindowStart    time.Time              `json:"window_start"`
	WindowEnd      time.Time              `json:"window_end"`
	TotalArticles  int                    `json:"total_articles"`
	ArticlesBySource map[string]int       `json:"articles_by_source"`
	ArticlesByType  map[string]int        `json:"articles_by_type"`
	AvgTitleLength float64                `json:"avg_title_length"`
	AvgDescLength  float64                `json:"avg_desc_length"`
	TopCategories  map[string]int         `json:"top_categories"`
	PublishingRate float64                `json:"publishing_rate"` // articles per second
	Metadata       map[string]interface{} `json:"metadata"`
}

// Aggregator manages tumbling window aggregation
type Aggregator struct {
	config      AggregationConfig
	windowStart time.Time
	articles    []Article
	stats       AggregatedStats
	mu          sync.RWMutex
	flushChan   chan AggregatedStats
	stopChan    chan struct{}
}

// DefaultAggregationConfig returns default aggregation configuration
func DefaultAggregationConfig() AggregationConfig {
	return AggregationConfig{
		Enabled:          false,
		WindowType:       "time",
		WindowSize:       60, // 60 seconds
		MaxWindowSize:    1000,
		AggregationTypes: []string{"basic", "source_stats", "text_analysis"},
	}
}

// NewAggregator creates a new aggregator
func NewAggregator(config AggregationConfig) *Aggregator {
	agg := &Aggregator{
		config:      config,
		windowStart: time.Now(),
		articles:    make([]Article, 0, config.MaxWindowSize),
		flushChan:   make(chan AggregatedStats, 10),
		stopChan:    make(chan struct{}),
	}
	
	// Initialize stats
	agg.stats = AggregatedStats{
		WindowStart:     agg.windowStart,
		ArticlesBySource: make(map[string]int),
		ArticlesByType:   make(map[string]int),
		TopCategories:    make(map[string]int),
		Metadata:         make(map[string]interface{}),
	}
	
	if config.Enabled {
		go agg.windowMonitor()
	}
	
	return agg
}

// AddArticle adds an article to the current window
func (a *Aggregator) AddArticle(article Article) {
	a.mu.Lock()
	defer a.mu.Unlock()
	
	a.articles = append(a.articles, article)
	
	// Update running statistics
	a.updateRunningStats(article)
	
	// Check if window should be flushed based on count
	if a.config.WindowType == "count" && len(a.articles) >= a.config.WindowSize {
		a.flushWindow()
	}
	
	// Safety check: don't exceed max window size
	if len(a.articles) >= a.config.MaxWindowSize {
		log.Printf("Window reached max size (%d), forcing flush", a.config.MaxWindowSize)
		a.flushWindow()
	}
}

// updateRunningStats updates running statistics without full recalculation
func (a *Aggregator) updateRunningStats(article Article) {
	// Update source counts
	a.stats.ArticlesBySource[article.Source]++
	
	// Update type counts
	a.stats.ArticlesByType[article.SourceType]++
	
	// Update category counts
	for _, category := range article.Categories {
		a.stats.TopCategories[category]++
	}
	
	// Update total articles
	a.stats.TotalArticles = len(a.articles)
	
	// Update window end time
	a.stats.WindowEnd = time.Now()
	
	// Calculate publishing rate
	windowDuration := a.stats.WindowEnd.Sub(a.stats.WindowStart).Seconds()
	if windowDuration > 0 {
		a.stats.PublishingRate = float64(a.stats.TotalArticles) / windowDuration
	}
}

// calculateAggregatedStats calculates complete statistics for current window
func (a *Aggregator) calculateAggregatedStats() AggregatedStats {
	a.mu.RLock()
	defer a.mu.RUnlock()
	
	if len(a.articles) == 0 {
		return a.stats
	}
	
	// Calculate text statistics
	var totalTitleLength, totalDescLength int
	for _, article := range a.articles {
		totalTitleLength += len(article.Title)
		totalDescLength += len(article.Description)
	}
	
	a.stats.AvgTitleLength = float64(totalTitleLength) / float64(len(a.articles))
	a.stats.AvgDescLength = float64(totalDescLength) / float64(len(a.articles))
	
	// Add metadata
	a.stats.Metadata["article_count"] = len(a.articles)
	a.stats.Metadata["window_duration_seconds"] = a.stats.WindowEnd.Sub(a.stats.WindowStart).Seconds()
	a.stats.Metadata["config"] = a.config
	
	return a.stats
}

// flushWindow flushes the current window and starts a new one
func (a *Aggregator) flushWindow() {
	a.mu.Lock()
	defer a.mu.Unlock()
	
	if len(a.articles) == 0 {
		// No articles to flush, just reset window
		a.windowStart = time.Now()
		a.stats = AggregatedStats{
			WindowStart:      a.windowStart,
			ArticlesBySource: make(map[string]int),
			ArticlesByType:   make(map[string]int),
			TopCategories:    make(map[string]int),
			Metadata:         make(map[string]interface{}),
		}
		return
	}
	
	// Calculate final statistics
	finalStats := a.calculateAggregatedStats()
	
	// Send to flush channel
	select {
	case a.flushChan <- finalStats:
		log.Printf("Flushed aggregation window: %d articles, %.1f articles/sec", 
			finalStats.TotalArticles, finalStats.PublishingRate)
	default:
		log.Printf("Warning: flush channel full, dropping aggregated stats")
	}
	
	// Reset for new window
	a.articles = make([]Article, 0, a.config.MaxWindowSize)
	a.windowStart = time.Now()
	a.stats = AggregatedStats{
		WindowStart:      a.windowStart,
		ArticlesBySource: make(map[string]int),
		ArticlesByType:   make(map[string]int),
		TopCategories:    make(map[string]int),
		Metadata:         make(map[string]interface{}),
	}
}

// windowMonitor monitors time-based windows
func (a *Aggregator) windowMonitor() {
	if a.config.WindowType != "time" {
		return
	}
	
	ticker := time.NewTicker(time.Duration(a.config.WindowSize) * time.Second)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			a.flushWindow()
		case <-a.stopChan:
			return
		}
	}
}

// GetFlushChannel returns the channel that receives flushed statistics
func (a *Aggregator) GetFlushChannel() <-chan AggregatedStats {
	return a.flushChan
}

// Stop stops the aggregator
func (a *Aggregator) Stop() {
	close(a.stopChan)
	
	// Flush any remaining articles
	a.flushWindow()
	
	close(a.flushChan)
}

// MarshalJSON converts aggregated stats to JSON
func (as AggregatedStats) MarshalJSON() ([]byte, error) {
	type Alias AggregatedStats
	return json.Marshal(&struct {
		WindowStart string `json:"window_start"`
		WindowEnd   string `json:"window_end"`
		Alias
	}{
		WindowStart: as.WindowStart.Format(time.RFC3339),
		WindowEnd:   as.WindowEnd.Format(time.RFC3339),
		Alias:       (Alias)(as),
	})
}

// AggregationManager manages multiple aggregators
type AggregationManager struct {
	aggregators map[string]*Aggregator
	config      map[string]AggregationConfig
	mu          sync.RWMutex
}

// NewAggregationManager creates a new aggregation manager
func NewAggregationManager() *AggregationManager {
	return &AggregationManager{
		aggregators: make(map[string]*Aggregator),
		config:      make(map[string]AggregationConfig),
	}
}

// AddAggregator adds a new aggregator with given name and config
func (am *AggregationManager) AddAggregator(name string, config AggregationConfig) {
	am.mu.Lock()
	defer am.mu.Unlock()
	
	am.config[name] = config
	am.aggregators[name] = NewAggregator(config)
}

// AddArticle adds an article to all aggregators
func (am *AggregationManager) AddArticle(article Article) {
	am.mu.RLock()
	defer am.mu.RUnlock()
	
	for _, aggregator := range am.aggregators {
		aggregator.AddArticle(article)
	}
}

// GetAggregator returns an aggregator by name
func (am *AggregationManager) GetAggregator(name string) (*Aggregator, bool) {
	am.mu.RLock()
	defer am.mu.RUnlock()
	
	agg, exists := am.aggregators[name]
	return agg, exists
}

// StopAll stops all aggregators
func (am *AggregationManager) StopAll() {
	am.mu.Lock()
	defer am.mu.Unlock()
	
	for _, aggregator := range am.aggregators {
		aggregator.Stop()
	}
	
	am.aggregators = make(map[string]*Aggregator)
	am.config = make(map[string]AggregationConfig)
}