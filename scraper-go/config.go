package main

// RSSSource represents a news source configuration
type RSSSource struct {
	URL  string
	Name string
	Type string // "rss" or "html"
}

// ParserConfig contains parser configuration
type ParserConfig struct {
	MaxConcurrentRequests int
	RequestTimeout        int
	UserAgent             string
	OutputDir             string
	OutputFilename        string
	EnableValidation      bool // Enable Rust validation
	Broker                BrokerConfig // Message broker configuration
}

// LogConfig contains logging configuration
type LogConfig struct {
	Level  string
	Format string
	File   string
}

// RSSSources is a list of news sources for testing
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
		URL:  "https://ria.ru/export/rss2/index.xml",
		Name: "RIA Novosti",
		Type: "rss",
	},
	{
		URL:  "https://www.bbc.com/russian/news",
		Name: "BBC Russian",
		Type: "html", // For HTML parsing demonstration
	},
}

// Config is the global configuration
var Config = ParserConfig{
	MaxConcurrentRequests: 10,
	RequestTimeout:        30,
	UserAgent:             "NewsScraper/1.0 (Go http.Client)",
	OutputDir:             "data",
	OutputFilename:        "news_data.json",
	EnableValidation:      true, // Enable validation by default
	Broker:                DefaultBrokerConfig(),
}

// LogCfg is the logging configuration
var LogCfg = LogConfig{
	Level:  "INFO",
	Format: "2006-01-02 15:04:05 - %s - %s - %s",
	File:   "scraper.log",
}