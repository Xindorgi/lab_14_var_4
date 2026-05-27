package main

import (
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// Metrics holds all Prometheus metrics for the scraper
type Metrics struct {
	// Scraping metrics
	articlesScrapedTotal prometheus.Counter
	articlesValidatedTotal prometheus.Counter
	articlesPublishedTotal prometheus.Counter
	scrapingErrorsTotal prometheus.Counter
	validationErrorsTotal prometheus.Counter
	publishingErrorsTotal prometheus.Counter

	// Timing metrics
	scrapeDuration prometheus.Histogram
	validationDuration prometheus.Histogram
	publishingDuration prometheus.Histogram

	// Aggregation metrics
	aggregationWindowsTotal prometheus.Counter
	aggregatedArticlesTotal prometheus.Counter
	aggregationErrorsTotal prometheus.Counter

	// Coordination metrics
	etcdHeartbeatsTotal prometheus.Counter
	etcdLockAcquisitionsTotal prometheus.Counter
	etcdLockFailuresTotal prometheus.Counter

	// Broker metrics
	brokerMessagesSentTotal prometheus.Counter
	brokerMessagesFailedTotal prometheus.Counter
	brokerBatchSize prometheus.Histogram

	// System metrics
	activeGoroutines prometheus.Gauge
	heapAllocBytes prometheus.Gauge
}

var (
	metrics *Metrics
)

// InitMetrics initializes Prometheus metrics
func InitMetrics() *Metrics {
	if metrics != nil {
		return metrics
	}

	metrics = &Metrics{
		articlesScrapedTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_articles_scraped_total",
			Help: "Total number of articles scraped",
		}),
		articlesValidatedTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_articles_validated_total",
			Help: "Total number of articles validated",
		}),
		articlesPublishedTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_articles_published_total",
			Help: "Total number of articles published to broker",
		}),
		scrapingErrorsTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_scraping_errors_total",
			Help: "Total number of scraping errors",
		}),
		validationErrorsTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_validation_errors_total",
			Help: "Total number of validation errors",
		}),
		publishingErrorsTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_publishing_errors_total",
			Help: "Total number of publishing errors",
		}),
		scrapeDuration: promauto.NewHistogram(prometheus.HistogramOpts{
			Name:    "scraper_scrape_duration_seconds",
			Help:    "Duration of scraping operations in seconds",
			Buckets: prometheus.DefBuckets,
		}),
		validationDuration: promauto.NewHistogram(prometheus.HistogramOpts{
			Name:    "scraper_validation_duration_seconds",
			Help:    "Duration of validation operations in seconds",
			Buckets: prometheus.DefBuckets,
		}),
		publishingDuration: promauto.NewHistogram(prometheus.HistogramOpts{
			Name:    "scraper_publishing_duration_seconds",
			Help:    "Duration of publishing operations in seconds",
			Buckets: prometheus.DefBuckets,
		}),
		aggregationWindowsTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_aggregation_windows_total",
			Help: "Total number of aggregation windows processed",
		}),
		aggregatedArticlesTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_aggregated_articles_total",
			Help: "Total number of articles aggregated",
		}),
		aggregationErrorsTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_aggregation_errors_total",
			Help: "Total number of aggregation errors",
		}),
		etcdHeartbeatsTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_etcd_heartbeats_total",
			Help: "Total number of etcd heartbeats sent",
		}),
		etcdLockAcquisitionsTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_etcd_lock_acquisitions_total",
			Help: "Total number of etcd lock acquisitions",
		}),
		etcdLockFailuresTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_etcd_lock_failures_total",
			Help: "Total number of etcd lock failures",
		}),
		brokerMessagesSentTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_broker_messages_sent_total",
			Help: "Total number of messages sent to broker",
		}),
		brokerMessagesFailedTotal: promauto.NewCounter(prometheus.CounterOpts{
			Name: "scraper_broker_messages_failed_total",
			Help: "Total number of failed broker messages",
		}),
		brokerBatchSize: promauto.NewHistogram(prometheus.HistogramOpts{
			Name:    "scraper_broker_batch_size",
			Help:    "Size of batches sent to broker",
			Buckets: prometheus.LinearBuckets(1, 10, 20), // 1 to 200
		}),
		activeGoroutines: promauto.NewGauge(prometheus.GaugeOpts{
			Name: "scraper_goroutines_active",
			Help: "Number of active goroutines",
		}),
		heapAllocBytes: promauto.NewGauge(prometheus.GaugeOpts{
			Name: "scraper_heap_alloc_bytes",
			Help: "Heap allocation in bytes",
		}),
	}

	return metrics
}

// GetMetrics returns the global metrics instance
func GetMetrics() *Metrics {
	if metrics == nil {
		return InitMetrics()
	}
	return metrics
}

// StartMetricsServer starts HTTP server for metrics and health endpoints
func StartMetricsServer(port int) error {
	// Initialize metrics if not already done
	InitMetrics()

	mux := http.NewServeMux()
	
	// Prometheus metrics endpoint
	mux.Handle("/metrics", promhttp.Handler())
	
	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status": "healthy", "timestamp": "%s"}`, time.Now().UTC().Format(time.RFC3339))
	})
	
	// Ready check endpoint
	mux.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status": "ready", "timestamp": "%s"}`, time.Now().UTC().Format(time.RFC3339))
	})

	// Root endpoint with basic info
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintln(w, "News Scraper Metrics Server")
		fmt.Fprintln(w, "Endpoints:")
		fmt.Fprintln(w, "  /metrics - Prometheus metrics")
		fmt.Fprintln(w, "  /health  - Health check")
		fmt.Fprintln(w, "  /ready   - Readiness check")
	})

	addr := fmt.Sprintf(":%d", port)
	log.Printf("Starting metrics server on %s", addr)
	
	// Start server in background
	go func() {
		if err := http.ListenAndServe(addr, mux); err != nil {
			log.Printf("Metrics server error: %v", err)
		}
	}()

	return nil
}

// UpdateSystemMetrics updates system-level metrics
func UpdateSystemMetrics() {
	if metrics == nil {
		return
	}
	
	// Update goroutine count
	// Note: This is a simple implementation; in production you might want
	// to use runtime.NumGoroutine() and runtime.ReadMemStats()
	// For now, we'll leave these as placeholders that can be updated
	// by calling code when appropriate
}

// RecordScrapeDuration records the duration of a scrape operation
func (m *Metrics) RecordScrapeDuration(duration time.Duration) {
	m.scrapeDuration.Observe(duration.Seconds())
}

// RecordValidationDuration records the duration of a validation operation
func (m *Metrics) RecordValidationDuration(duration time.Duration) {
	m.validationDuration.Observe(duration.Seconds())
}

// RecordPublishingDuration records the duration of a publishing operation
func (m *Metrics) RecordPublishingDuration(duration time.Duration) {
	m.publishingDuration.Observe(duration.Seconds())
}

// RecordBrokerBatchSize records the size of a batch sent to broker
func (m *Metrics) RecordBrokerBatchSize(size int) {
	m.brokerBatchSize.Observe(float64(size))
}