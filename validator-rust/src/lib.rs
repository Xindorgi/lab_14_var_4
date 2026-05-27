//! News article validation library
//! 
//! Provides validation functions for news article data including:
//! - Date format validation and parsing
//! - HTML sanitization (basic tag removal)
//! - URL validation and normalization
//! - Field length and format checks

use regex::Regex;
use chrono::{DateTime, FixedOffset, NaiveDateTime, Utc};
use url::{Url, Position};
use std::error::Error;
use std::fmt;
use lazy_static::lazy_static;
use thiserror::Error as ThisError;

/// Validation error types
#[derive(Debug, ThisError)]
pub enum ValidationError {
    #[error("Invalid date format: {0}")]
    InvalidDateFormat(String),
    
    #[error("Date is in the future: {0}")]
    FutureDate(String),
    
    #[error("Date is too old (before 2000): {0}")]
    TooOldDate(String),
    
    #[error("Invalid URL: {0}")]
    InvalidUrl(String),
    
    #[error("URL scheme not allowed: {0}")]
    InvalidUrlScheme(String),
    
    #[error("Title is empty or too short")]
    InvalidTitle,
    
    #[error("Title is too long (max {0} characters)")]
    TitleTooLong(usize),
    
    #[error("Description is too long (max {0} characters)")]
    DescriptionTooLong(usize),
    
    #[error("HTML contains potentially dangerous content")]
    DangerousHtmlContent,
    
    #[error("Field validation failed: {0}")]
    FieldValidation(String),
}

/// Validation result type
pub type ValidationResult<T> = Result<T, ValidationError>;

/// News article structure for validation
#[derive(Debug, Clone)]
pub struct NewsArticle {
    pub title: String,
    pub link: String,
    pub description: String,
    pub published: String,
    pub source: String,
}

/// Validation configuration
#[derive(Debug, Clone)]
pub struct ValidationConfig {
    pub max_title_length: usize,
    pub max_description_length: usize,
    pub allowed_url_schemes: Vec<String>,
    pub allow_future_dates: bool,
    pub min_year: i32,
    pub html_sanitize: bool,
    pub remove_script_tags: bool,
}

impl Default for ValidationConfig {
    fn default() -> Self {
        Self {
            max_title_length: 500,
            max_description_length: 5000,
            allowed_url_schemes: vec!["http".to_string(), "https".to_string()],
            allow_future_dates: false,
            min_year: 2000,
            html_sanitize: true,
            remove_script_tags: true,
        }
    }
}

lazy_static! {
    static ref DATE_REGEXES: Vec<(&'static str, &'static str)> = vec![
        (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "%Y-%m-%dT%H:%M:%SZ"), // ISO 8601 UTC
        (r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"), // SQL datetime
        (r"\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2} [+-]\d{4}", "%a, %d %b %Y %H:%M:%S %z"), // RFC 1123
        (r"\d{2}/\d{2}/\d{4}", "%m/%d/%Y"), // US date
        (r"\d{2}\.\d{2}\.\d{4}", "%d.%m.%Y"), // EU date
    ];
    
    static ref URL_REGEX: Regex = Regex::new(r"^https?://[^\s/$.?#].[^\s]*$").unwrap();
    static ref HTML_TAG_REGEX: Regex = Regex::new(r"<[^>]*>").unwrap();
    static ref SCRIPT_TAG_REGEX: Regex = Regex::new(r"<script[^>]*>.*?</script>").unwrap();
    static ref DANGEROUS_ATTR_REGEX: Regex = Regex::new(r"on\w+\s*=").unwrap();
}

/// Validate and parse a date string
pub fn validate_date(date_str: &str, config: &ValidationConfig) -> ValidationResult<DateTime<Utc>> {
    if date_str.trim().is_empty() {
        return Ok(Utc::now()); // Empty date defaults to now
    }
    
    // Try each known date format
    for (pattern, format) in DATE_REGEXES.iter() {
        let re = Regex::new(pattern).unwrap();
        if re.is_match(date_str) {
            // Try parsing with timezone offset first
            if let Ok(dt) = DateTime::parse_from_str(date_str, format) {
                let utc_dt = dt.with_timezone(&Utc);
                return check_date_limits(&utc_dt, config);
            }
            
            // Try without timezone
            if let Ok(ndt) = NaiveDateTime::parse_from_str(date_str, format) {
                let utc_dt = DateTime::<Utc>::from_naive_utc_and_offset(ndt, Utc);
                return check_date_limits(&utc_dt, config);
            }
        }
    }
    
    // Try chrono's built-in parser as fallback
    if let Ok(dt) = date_str.parse::<DateTime<FixedOffset>>() {
        let utc_dt = dt.with_timezone(&Utc);
        return check_date_limits(&utc_dt, config);
    }
    
    if let Ok(dt) = date_str.parse::<DateTime<Utc>>() {
        return check_date_limits(&dt, config);
    }
    
    Err(ValidationError::InvalidDateFormat(date_str.to_string()))
}

fn check_date_limits(dt: &DateTime<Utc>, config: &ValidationConfig) -> ValidationResult<DateTime<Utc>> {
    let now = Utc::now();
    
    // Check if date is in the future (unless allowed)
    if dt > &now && !config.allow_future_dates {
        return Err(ValidationError::FutureDate(dt.to_rfc3339()));
    }
    
    // Check if date is too old
    if dt.year() < config.min_year {
        return Err(ValidationError::TooOldDate(dt.to_rfc3339()));
    }
    
    Ok(*dt)
}

/// Validate a URL
pub fn validate_url(url_str: &str, config: &ValidationConfig) -> ValidationResult<String> {
    if url_str.trim().is_empty() {
        return Err(ValidationError::InvalidUrl("URL is empty".to_string()));
    }
    
    // Basic regex check first
    if !URL_REGEX.is_match(url_str) {
        return Err(ValidationError::InvalidUrl(url_str.to_string()));
    }
    
    // Parse with URL crate for more thorough validation
    let parsed_url = match Url::parse(url_str) {
        Ok(url) => url,
        Err(e) => return Err(ValidationError::InvalidUrl(format!("{}: {}", url_str, e))),
    };
    
    // Check allowed schemes
    let scheme = parsed_url.scheme();
    if !config.allowed_url_schemes.iter().any(|s| s == scheme) {
        return Err(ValidationError::InvalidUrlScheme(scheme.to_string()));
    }
    
    // Normalize URL (remove fragment, sort query params, etc.)
    let normalized = parsed_url[..Position::AfterPath].to_string();
    
    Ok(normalized)
}

/// Sanitize HTML content
pub fn sanitize_html(html: &str, config: &ValidationConfig) -> String {
    let mut result = html.to_string();
    
    // Remove script tags if configured
    if config.remove_script_tags {
        result = SCRIPT_TAG_REGEX.replace_all(&result, "").to_string();
    }
    
    // Check for dangerous attributes
    if DANGEROUS_ATTR_REGEX.is_match(&result) {
        // Remove dangerous attributes
        result = DANGEROUS_ATTR_REGEX.replace_all(&result, "data-removed=").to_string();
    }
    
    // Remove all HTML tags if sanitization is enabled
    if config.html_sanitize {
        result = HTML_TAG_REGEX.replace_all(&result, "").to_string();
        // Decode HTML entities (basic)
        result = result.replace("&amp;", "&")
                      .replace("&lt;", "<")
                      .replace("&gt;", ">")
                      .replace("&quot;", "\"")
                      .replace("&#39;", "'");
    }
    
    result.trim().to_string()
}

/// Validate article title
pub fn validate_title(title: &str, config: &ValidationConfig) -> ValidationResult<String> {
    let trimmed = title.trim();
    
    if trimmed.is_empty() {
        return Err(ValidationError::InvalidTitle);
    }
    
    if trimmed.len() > config.max_title_length {
        return Err(ValidationError::TitleTooLong(config.max_title_length));
    }
    
    Ok(trimmed.to_string())
}

/// Validate article description
pub fn validate_description(description: &str, config: &ValidationConfig) -> ValidationResult<String> {
    let sanitized = if config.html_sanitize {
        sanitize_html(description, config)
    } else {
        description.trim().to_string()
    };
    
    if sanitized.len() > config.max_description_length {
        return Err(ValidationError::DescriptionTooLong(config.max_description_length));
    }
    
    Ok(sanitized)
}

/// Validate a complete news article
pub fn validate_article(article: &NewsArticle, config: &ValidationConfig) -> ValidationResult<NewsArticle> {
    let title = validate_title(&article.title, config)?;
    let link = validate_url(&article.link, config)?;
    let description = validate_description(&article.description, config)?;
    let published = validate_date(&article.published, config)?.to_rfc3339();
    let source = article.source.trim().to_string();
    
    if source.is_empty() {
        return Err(ValidationError::FieldValidation("Source cannot be empty".to_string()));
    }
    
    Ok(NewsArticle {
        title,
        link,
        description,
        published,
        source,
    })
}

/// C-compatible interface for FFI
mod ffi {
    use super::*;
    use std::ffi::{CStr, CString};
    use std::os::raw::c_char;
    
    /// C-compatible validation configuration
    #[repr(C)]
    pub struct CValidationConfig {
        max_title_length: usize,
        max_description_length: usize,
        allow_future_dates: bool,
        min_year: i32,
        html_sanitize: bool,
    }
    
    /// Validate a news article (C interface)
    /// Returns JSON string with validation results or error message
    /// Caller must free the returned string using free_c_string
    #[no_mangle]
    pub extern "C" fn validate_news_article(
        title: *const c_char,
        link: *const c_char,
        description: *const c_char,
        published: *const c_char,
        source: *const c_char,
        config: *const CValidationConfig,
    ) -> *mut c_char {
        // Convert C strings to Rust strings
        let title_str = unsafe { CStr::from_ptr(title).to_string_lossy().into_owned() };
        let link_str = unsafe { CStr::from_ptr(link).to_string_lossy().into_owned() };
        let description_str = unsafe { CStr::from_ptr(description).to_string_lossy().into_owned() };
        let published_str = unsafe { CStr::from_ptr(published).to_string_lossy().into_owned() };
        let source_str = unsafe { CStr::from_ptr(source).to_string_lossy().into_owned() };
        
        // Convert C config to Rust config
        let rust_config = if config.is_null() {
            ValidationConfig::default()
        } else {
            let c_config = unsafe { &*config };
            ValidationConfig {
                max_title_length: c_config.max_title_length,
                max_description_length: c_config.max_description_length,
                allowed_url_schemes: vec!["http".to_string(), "https".to_string()],
                allow_future_dates: c_config.allow_future_dates,
                min_year: c_config.min_year,
                html_sanitize: c_config.html_sanitize,
                remove_script_tags: true,
            }
        };
        
        // Create article
        let article = NewsArticle {
            title: title_str,
            link: link_str,
            description: description_str,
            published: published_str,
            source: source_str,
        };
        
        // Validate article
        match validate_article(&article, &rust_config) {
            Ok(validated) => {
                // Create JSON response
                let response = serde_json::json!({
                    "success": true,
                    "validated_article": {
                        "title": validated.title,
                        "link": validated.link,
                        "description": validated.description,
                        "published": validated.published,
                        "source": validated.source,
                    }
                });
                
                CString::new(response.to_string())
                    .unwrap()
                    .into_raw()
            }
            Err(err) => {
                let response = serde_json::json!({
                    "success": false,
                    "error": err.to_string(),
                });
                
                CString::new(response.to_string())
                    .unwrap()
                    .into_raw()
            }
        }
    }
    
    /// Free a string returned by validate_news_article
    #[no_mangle]
    pub extern "C" fn free_c_string(s: *mut c_char) {
        unsafe {
            if s.is_null() {
                return;
            }
            let _ = CString::from_raw(s);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_validate_date() {
        let config = ValidationConfig::default();
        
        // Valid dates
        assert!(validate_date("2024-01-01T12:00:00Z", &config).is_ok());
        assert!(validate_date("Mon, 01 Jan 2024 12:00:00 +0000", &config).is_ok());
        
        // Invalid dates
        assert!(validate_date("not a date", &config).is_err());
        assert!(validate_date("1999-01-01T12:00:00Z", &config).is_err()); // Too old
    }
    
    #[test]
    fn test_validate_url() {
        let config = ValidationConfig::default();
        
        // Valid URLs
        assert!(validate_url("https://example.com/news", &config).is_ok());
        assert!(validate_url("http://example.com/path?query=1", &config).is_ok());
        
        // Invalid URLs
        assert!(validate_url("not a url", &config).is_err());
        assert!(validate_url("ftp://example.com", &config).is_err()); // Wrong scheme
    }
    
    #[test]
    fn test_sanitize_html() {
        let config = ValidationConfig::default();
        
        let html = "<script>alert('xss')</script><p>Hello</p>";
        let sanitized = sanitize_html(html, &config);
        assert!(!sanitized.contains("script"));
        assert!(!sanitized.contains("<p>"));
    }
    
    #[test]
    fn test_validate_title() {
        let config = ValidationConfig::default();
        
        assert!(validate_title("Valid Title", &config).is_ok());
        assert!(validate_title("", &config).is_err());
        
        let long_title = "a".repeat(600);
        assert!(validate_title(&long_title, &config).is_err());
    }
    
    #[test]
    fn test_validate_article() {
        let config = ValidationConfig::default();
        
        let article = NewsArticle {
            title: "Test News".to_string(),
            link: "https://example.com/news".to_string(),
            description: "Test description".to_string(),
            published: "2024-01-01T12:00:00Z".to_string(),
            source: "Test Source".to_string(),
        };
        
        assert!(validate_article(&article, &config).is_ok());
    }
}