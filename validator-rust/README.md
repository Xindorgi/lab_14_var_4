# News Validator (Rust)

A Rust library for validating news article data with C bindings for integration with Go and other languages.

## Features

- **Date Validation**: Multiple date format support with range checking
- **URL Validation**: Scheme checking and normalization
- **HTML Sanitization**: Script tag removal and dangerous attribute filtering
- **Field Validation**: Title and description length checks
- **C Bindings**: FFI interface for integration with C/C++, Go, Python, etc.

## Usage

### As a Rust Library

Add to your `Cargo.toml`:

```toml
[dependencies]
news-validator = { path = "../validator-rust" }
```

Example usage:

```rust
use news_validator::{validate_article, NewsArticle, ValidationConfig};

let config = ValidationConfig::default();
let article = NewsArticle {
    title: "Breaking News".to_string(),
    link: "https://example.com/news".to_string(),
    description: "<p>News content</p>".to_string(),
    published: "2024-01-01T12:00:00Z".to_string(),
    source: "Example News".to_string(),
};

match validate_article(&article, &config) {
    Ok(validated) => println!("Validated article: {:?}", validated),
    Err(err) => eprintln!("Validation error: {}", err),
}
```

### C Interface

The library provides a C-compatible interface:

```c
#include "news_validator.h"

// Validate a news article
char* result = validate_news_article(
    "Breaking News",
    "https://example.com/news",
    "<p>News content</p>",
    "2024-01-01T12:00:00Z",
    "Example News",
    NULL  // Use default config
);

// Result is a JSON string
printf("Validation result: %s\n", result);

// Free the string when done
free_c_string(result);
```

### Go Integration (via cgo)

See the Go scraper integration for example usage.

## Validation Rules

### Date Validation
- Supports multiple formats: ISO 8601, RFC 1123, SQL datetime, etc.
- Rejects dates before year 2000 (configurable)
- Rejects future dates (configurable)
- Empty dates default to current time

### URL Validation
- Requires http:// or https:// scheme
- Validates URL structure
- Normalizes URLs (removes fragments, sorts query params)

### HTML Sanitization
- Removes `<script>` tags
- Filters dangerous attributes (onclick, onload, etc.)
- Optionally removes all HTML tags
- Decodes HTML entities

### Field Validation
- Title: 1-500 characters (configurable)
- Description: 0-5000 characters (configurable)
- Source: Cannot be empty

## Building

### Rust Library

```bash
cd validator-rust
cargo build --release
```

### C Bindings

C bindings are automatically generated during build. The header file is created at `include/news_validator.h`.

### Static Library

To build a static library for C integration:

```bash
cargo build --release --lib
# Library will be at target/release/libnews_validator.a
```

## Integration Examples

### Go (cgo)

```go
// #cgo LDFLAGS: -L${SRCDIR}/validator-rust/target/release -lnews_validator -lm -ldl
// #include "validator-rust/include/news_validator.h"
import "C"

func ValidateArticle(title, link, description, published, source string) (string, error) {
    cResult := C.validate_news_article(
        C.CString(title),
        C.CString(link),
        C.CString(description),
        C.CString(published),
        C.CString(source),
        nil,
    )
    defer C.free_c_string(cResult)
    
    result := C.GoString(cResult)
    // Parse JSON result...
    return result, nil
}
```

### Python (ctypes)

```python
import ctypes
import json

lib = ctypes.CDLL('target/release/libnews_validator.so')

lib.validate_news_article.argtypes = [
    ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
    ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p
]
lib.validate_news_article.restype = ctypes.c_char_p
lib.free_c_string.argtypes = [ctypes.c_char_p]

def validate_article(title, link, description, published, source):
    result = lib.validate_news_article(
        title.encode(), link.encode(), description.encode(),
        published.encode(), source.encode(), None
    )
    json_result = json.loads(result.decode())
    lib.free_c_string(result)
    return json_result
```

## Configuration

### ValidationConfig

```rust
pub struct ValidationConfig {
    pub max_title_length: usize,        // Default: 500
    pub max_description_length: usize,  // Default: 5000
    pub allowed_url_schemes: Vec<String>, // Default: ["http", "https"]
    pub allow_future_dates: bool,       // Default: false
    pub min_year: i32,                  // Default: 2000
    pub html_sanitize: bool,            // Default: true
    pub remove_script_tags: bool,       // Default: true
}
```

### C Configuration

```c
typedef struct {
    size_t max_title_length;
    size_t max_description_length;
    bool allow_future_dates;
    int min_year;
    bool html_sanitize;
} CValidationConfig;
```

## Error Handling

The library returns detailed error messages:

```rust
pub enum ValidationError {
    InvalidDateFormat(String),
    FutureDate(String),
    TooOldDate(String),
    InvalidUrl(String),
    InvalidUrlScheme(String),
    InvalidTitle,
    TitleTooLong(usize),
    DescriptionTooLong(usize),
    DangerousHtmlContent,
    FieldValidation(String),
}
```

C interface returns JSON with success/error information.

## Testing

Run tests:

```bash
cargo test
```

Test coverage includes:
- Date parsing and validation
- URL validation and normalization
- HTML sanitization
- Field length checks
- Complete article validation

## Dependencies

- `regex`: Regular expressions for pattern matching
- `chrono`: Date and time parsing
- `url`: URL parsing and normalization
- `lazy_static`: Compile-time regex compilation
- `thiserror`: Error type generation
- `cbindgen`: C binding generation

## License

MIT OR Apache-2.0