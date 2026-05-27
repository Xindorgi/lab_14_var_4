package main

import "time"

// RSSSource represents a news source configuration
type RSSSource struct {
	URL  string
	Name string
	Type string // "rss" or "html"
}

// ParserConfig contains parser configuration
type ParserConfig struct {
	// Basic settings
	MaxConcurrentRequests int
	RequestTimeout        int    // seconds
	UserAgent             string
	OutputDir             string
	OutputFilename        string
	EnableValidation      bool

	// Broker configuration
	Broker BrokerConfig

	// etcd coordination
	Etcd EtcdConfig

	// Aggregation configuration
	Aggregation AggregationConfig

	// Arrow Flight configuration
	ArrowFlight ArrowFlightConfig
}

// Default configuration values
var Config = ParserConfig{
	// Basic settings
	MaxConcurrentRequests: 10,
	RequestTimeout:        30,
	UserAgent:             "NewsScraper/1.0 (Go http.Client)",
	OutputDir:             "data",
	OutputFilename:        "news_data.json",
	EnableValidation:      true,

	// Broker configuration
	Broker: DefaultBrokerConfig(),

	// etcd coordination
	Etcd: DefaultEtcdConfig(),

	// Aggregation configuration
	Aggregation: DefaultAggregationConfig(),

	// Arrow Flight configuration
	ArrowFlight: DefaultArrowFlightConfig(),
}

// RSS sources to scrape
var RSSSources = []RSSSource{
	{
		URL:  "https://lenta.ru/rss/news",
		Name: "Lenta.ru News",
		Type: "rss",
	},
	{
		URL:  "https://www.interfax.ru/rss.asp",
		Name: "Interfax",
		Type: "rss",
	},
	{
		URL:  "https://ria.ru/export/rss2/archive/index.xml",
		Name: "RIA Novosti",
		Type: "rss",
	},
	{
		URL:  "https://www.bbc.com/russian",
		Name: "BBC Russian",
		Type: "html",
	},
}