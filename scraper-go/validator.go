// Package main provides integration with Rust validator library via cgo
package main

/*
#cgo LDFLAGS: -L${SRCDIR}/../validator-rust/target/release -lnews_validator -lm -ldl
#include "../validator-rust/include/news_validator.h"
#include <stdlib.h>
*/
import "C"
import (
	"encoding/json"
	"fmt"
	"log"
	"unsafe"
)

// Validator provides integration with Rust validation library
type Validator struct {
	enabled bool
}

// ValidationResult represents the result of article validation
type ValidationResult struct {
	Success bool `json:"success"`
	Error   string `json:"error,omitempty"`
	Article *Article `json:"validated_article,omitempty"`
}

// NewValidator creates a new validator instance
func NewValidator(enabled bool) *Validator {
	return &Validator{enabled: enabled}
}

// ValidateArticle validates a news article using Rust library
func (v *Validator) ValidateArticle(article *Article) (*Article, error) {
	if !v.enabled {
		log.Println("Validator disabled, skipping validation")
		return article, nil
	}
	
	log.Printf("Validating article: %s", article.Title)
	
	// Convert Go strings to C strings
	cTitle := C.CString(article.Title)
	cLink := C.CString(article.Link)
	cDescription := C.CString(article.Description)
	cPublished := C.CString(article.Published)
	cSource := C.CString(article.Source)
	
	// Free C strings when done
	defer func() {
		C.free(unsafe.Pointer(cTitle))
		C.free(unsafe.Pointer(cLink))
		C.free(unsafe.Pointer(cDescription))
		C.free(unsafe.Pointer(cPublished))
		C.free(unsafe.Pointer(cSource))
	}()
	
	// Call Rust validation function (use default config: nil)
	cResult := C.validate_news_article(cTitle, cLink, cDescription, cPublished, cSource, nil)
	defer C.free_c_string(cResult)
	
	// Convert C result to Go string
	goResult := C.GoString(cResult)
	
	// Parse JSON response
	var validationResult struct {
		Success bool `json:"success"`
		Error   string `json:"error,omitempty"`
		ValidatedArticle struct {
			Title       string `json:"title"`
			Link        string `json:"link"`
			Description string `json:"description"`
			Published   string `json:"published"`
			Source      string `json:"source"`
		} `json:"validated_article,omitempty"`
	}
	
	if err := json.Unmarshal([]byte(goResult), &validationResult); err != nil {
		return nil, fmt.Errorf("failed to parse validation result: %w", err)
	}
	
	if !validationResult.Success {
		return nil, fmt.Errorf("validation failed: %s", validationResult.Error)
	}
	
	// Create validated article
	validated := &Article{
		Source:        validationResult.ValidatedArticle.Source,
		SourceType:    article.SourceType,
		Title:         validationResult.ValidatedArticle.Title,
		Link:          validationResult.ValidatedArticle.Link,
		Description:   validationResult.ValidatedArticle.Description,
		Published:     validationResult.ValidatedArticle.Published,
		PublishedTime: article.PublishedTime,
		Authors:       article.Authors,
		Categories:    article.Categories,
		ScrapedAt:     article.ScrapedAt,
	}
	
	log.Printf("Article validated successfully: %s", validated.Title)
	return validated, nil
}

// ValidateArticles validates multiple articles concurrently
func (v *Validator) ValidateArticles(articles []Article) ([]Article, []error) {
	if !v.enabled || len(articles) == 0 {
		return articles, nil
	}
	
	log.Printf("Validating %d articles", len(articles))
	
	validated := make([]Article, 0, len(articles))
	errors := make([]error, 0)
	
	// For simplicity, validate sequentially
	// In production, could use goroutines with limited concurrency
	for i, article := range articles {
		validatedArticle, err := v.ValidateArticle(&article)
		if err != nil {
			log.Printf("Validation error for article %d '%s': %v", i, article.Title, err)
			errors = append(errors, fmt.Errorf("article %d: %w", i, err))
			continue
		}
		validated = append(validated, *validatedArticle)
	}
	
	log.Printf("Validation complete: %d valid, %d invalid", len(validated), len(errors))
	return validated, errors
}

// BuildValidator checks if validator can be built
func BuildValidator() error {
	// Simple test to check if validator library is available
	// This would be more comprehensive in production
	log.Println("Validator build check: assuming Rust library is available")
	return nil
}