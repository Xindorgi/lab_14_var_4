# Go News Scraper

Concurrent RSS/HTML news scraper implemented in Go.

## Description

This module implements concurrent news scraping from various sources:
- RSS feeds (Lenta.ru, Interfax, RIA Novosti)
- HTML pages (BBC Russian)

Collected data is saved to a local JSON file for further processing.

## Features

- **Concurrent architecture**: Uses goroutines and channels for parallel processing
- **RSS and HTML support**: Universal parser for different source types
- **Configurable**: Easy to add new sources through configuration
- **Semaphore-based rate limiting**: Controls concurrent requests
- **JSON storage**: Structured data storage
- **Context support**: Proper timeout and cancellation handling

## Project Structure

```
scraper-go/
├── main.go              # Main scraper implementation
├── config.go            # Configuration and source definitions
├── go.mod               # Go module dependencies
└── README.md           # This documentation
```

## Installation

1. Ensure you have Go 1.21+ installed
2. Install dependencies:

```bash
go mod download
```

## Usage

### Running the scraper

```bash
go run main.go
```

### Building and running

```bash
go build -o news-scraper main.go
./news-scraper
```

### Configuration

Data sources are configured in `config.go`:

```go
var RSSSources = []RSSSource{
    {
        URL:  "https://lenta.ru/rss/news",
        Name: "Lenta.ru News",
        Type: "rss",
    },
    // ... other sources
}
```

### Parser settings

Configuration is available in `config.go`:

```go
var Config = ParserConfig{
    MaxConcurrentRequests: 10,    // Maximum concurrent requests
    RequestTimeout:        30,    // Request timeout in seconds
    UserAgent:             "NewsScraper/1.0 (Go http.Client)",
    OutputDir:             "data",             // Output directory
    OutputFilename:        "news_data.json",   // Output filename
}
```

## Output Data

Collected data is saved in JSON format to `data/news_data.json`:

```json
[
  {
    "source": "Lenta.ru News",
    "source_type": "rss",
    "title": "News headline",
    "link": "https://lenta.ru/news/...",
    "description": "News description...",
    "published": "Mon, 01 Jan 2024 12:00:00 +0300",
    "published_time": "2024-01-01T09:00:00Z",
    "authors": [],
    "categories": ["Politics"],
    "scraped_at": "2024-01-01T12:00:00Z"
  }
]
```

## Concurrency Model

The scraper uses a producer-consumer pattern with goroutines:

1. **Semaphore-based rate limiting**: Controls maximum concurrent HTTP requests
2. **Worker goroutines**: Each source is processed in a separate goroutine
3. **Channel-based communication**: Results and errors are collected through channels
4. **WaitGroup synchronization**: Ensures all goroutines complete before saving results

## Logging

Logs are written to stdout with timestamps:

```
2024-01-01 12:00:00 - Starting concurrent news scraper
2024-01-01 12:00:01 - Parsing RSS: Lenta.ru News
2024-01-01 12:00:02 - Found 20 articles in Lenta.ru News
```

## Extending Functionality

### Adding a new RSS source

1. Add a new source to `RSSSources` in `config.go`:

```go
RSSSource{
    URL:  "https://example.com/rss",
    Name: "Example News",
    Type: "rss",
}
```

### Adding a new HTML parser

1. Add a source with type "html" to `RSSSources`
2. Implement corresponding parsing logic in the `parseHTML()` method of `NewsScraper`

### Adjusting concurrency settings

Modify the `Config` in `config.go`:

```go
MaxConcurrentRequests: 20,    // Increase concurrent requests
RequestTimeout:        60,    // Increase timeout for slow sources
```

## Dependencies

- `github.com/mmcdole/gofeed`: RSS/Atom feed parsing
- `github.com/PuerkitoBio/goquery`: HTML parsing and traversal
- `golang.org/x/net`: HTTP client utilities
- `golang.org/x/sync`: Semaphore for rate limiting

## Testing

To test the scraper, use the built-in sources. Ensure you have internet access to make requests to news websites.

## Performance Considerations

- The semaphore prevents overwhelming servers with too many concurrent requests
- Context timeouts ensure the scraper doesn't hang on slow responses
- Channel buffers prevent goroutine blocking
- Memory usage is controlled by limiting the number of concurrent operations

## Notes

- Some websites may block requests without proper User-Agent headers
- HTML parser structure depends on specific websites and may require adaptation
- Always respect robots.txt and website terms of service
- Consider adding retry logic for transient failures