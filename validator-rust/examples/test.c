/*
 * Example C program using the Rust validator library
 * 
 * Compile with:
 * gcc -I../include test.c -L../target/release -lnews_validator -o test_validator
 * 
 * Run with:
 * LD_LIBRARY_PATH=../target/release ./test_validator
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../include/news_validator.h"

void test_validation(const char* title, const char* link, const char* description, 
                     const char* published, const char* source, const CValidationConfig* config) {
    printf("Testing validation:\n");
    printf("  Title: %s\n", title);
    printf("  Link: %s\n", link);
    printf("  Published: %s\n", published);
    printf("  Source: %s\n", source);
    
    char* result = validate_news_article(title, link, description, published, source, config);
    printf("  Result: %s\n\n", result);
    
    free_c_string(result);
}

int main() {
    printf("=== Rust Validator Library Test ===\n\n");
    
    // Test 1: Valid article
    printf("Test 1: Valid article\n");
    test_validation(
        "Breaking News: Important Event",
        "https://example.com/news/123",
        "This is a <strong>news</strong> article about an important event.",
        "2024-01-01T12:00:00Z",
        "Example News",
        NULL  // Use default config
    );
    
    // Test 2: Invalid URL
    printf("Test 2: Invalid URL\n");
    test_validation(
        "Another News",
        "not-a-valid-url",
        "Content",
        "2024-01-01T12:00:00Z",
        "Example News",
        NULL
    );
    
    // Test 3: Future date (if not allowed)
    printf("Test 3: Future date\n");
    test_validation(
        "Future News",
        "https://example.com/future",
        "News from the future",
        "2030-01-01T12:00:00Z",
        "Future News",
        NULL
    );
    
    // Test 4: Custom configuration
    printf("Test 4: Custom configuration (allow future dates)\n");
    CValidationConfig custom_config = {
        .max_title_length = 1000,
        .max_description_length = 10000,
        .allow_future_dates = true,
        .min_year = 1990,
        .html_sanitize = true
    };
    
    test_validation(
        "Future News Allowed",
        "https://example.com/future-allowed",
        "News from the future with custom config",
        "2030-01-01T12:00:00Z",
        "Future News",
        &custom_config
    );
    
    // Test 5: Script in description
    printf("Test 5: HTML with script tags\n");
    test_validation(
        "News with Script",
        "https://example.com/script",
        "<script>alert('xss')</script><p>Actual content</p>",
        "2024-01-01T12:00:00Z",
        "Test Source",
        NULL
    );
    
    // Test 6: Very old date
    printf("Test 6: Very old date\n");
    test_validation(
        "Old News",
        "https://example.com/old",
        "Very old news",
        "1990-01-01T12:00:00Z",
        "Old Source",
        NULL
    );
    
    printf("=== All tests completed ===\n");
    return 0;
}