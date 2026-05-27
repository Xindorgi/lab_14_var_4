# Performance Benchmarks

Load testing and performance comparison scripts for Python vs Go news scrapers.

## Overview

This directory contains scripts for:
1. Load testing Python scraper
2. Load testing Go scraper  
3. Comparing performance metrics
4. Generating visualizations and reports

## Requirements

Install benchmark dependencies:

```bash
pip install -r requirements.txt
```

For Go scraper testing, ensure Go 1.21+ is installed.

## Scripts

### 1. Load Test Python Scraper

```bash
python load_test_python.py
```

Runs the Python scraper multiple times and measures:
- Execution time
- CPU usage (average and peak)
- Memory consumption (average and peak)
- Exit codes

Results are saved to `benchmark_results/python_scraper_metrics_*.json`

### 2. Load Test Go Scraper

```bash
python load_test_go.py
```

Compiles (if needed) and runs the Go scraper multiple times, measuring the same metrics as above.

Results are saved to `benchmark_results/go_scraper_metrics_*.json`

### 3. Compare Results

```bash
python compare_results.py
```

Compares performance metrics between Python and Go scrapers and generates:
- Text report with detailed comparison
- JSON data file
- Visualization charts (PNG images)

## Output Files

All output files are saved to the `benchmark_results/` directory:

```
benchmark_results/
├── python_scraper_metrics_20240101_120000.json
├── go_scraper_metrics_20240101_120100.json
├── performance_comparison_report.txt
├── performance_comparison.json
├── performance_comparison.png
└── improvement_ratios.png
```

## Metrics Collected

For each scraper run, the following metrics are collected:

### Execution Metrics
- **Execution Time**: Total time to complete scraping
- **CPU Usage**: Average and maximum CPU percentage
- **Memory Usage**: Average and maximum RAM consumption in MB

### Statistical Summary
- Average across multiple runs
- Minimum and maximum values
- Standard deviation (implied)

## Performance Comparison

The comparison script analyzes:

1. **Execution Time**: Which scraper completes faster
2. **CPU Efficiency**: Which uses less CPU resources
3. **Memory Efficiency**: Which uses less memory
4. **Overall Performance**: Weighted comparison across all metrics

## Visualization

Two charts are generated:

1. **Performance Comparison Bar Chart**: Side-by-side comparison of all metrics
2. **Improvement Ratio Chart**: Shows how much better Go is compared to Python for each metric (values > 1 indicate Go is better)

## Running All Tests

Create a shell script or run sequentially:

```bash
# Run Python load test
python load_test_python.py

# Run Go load test  
python load_test_go.py

# Compare results
python compare_results.py
```

## Customization

### Adjusting Test Parameters

Modify the scripts to change:
- Number of iterations (default: 3)
- Sampling frequency (default: 200ms)
- Metrics collected

### Adding New Metrics

To add new performance metrics:

1. Add measurement code in the load test scripts
2. Update the metrics dictionary structure
3. Update comparison logic in `compare_results.py`

## Notes

- Ensure internet connectivity for scraper tests
- Results may vary based on system load and network conditions
- For consistent results, run tests on an isolated system
- The Go scraper needs to be compiled before testing (handled automatically)

## Troubleshooting

### psutil Not Found
```bash
pip install psutil
```

### matplotlib Not Found
```bash
pip install matplotlib numpy pandas
```

### Go Compilation Failed
- Ensure Go is installed and in PATH
- Check Go module dependencies: `go mod download` in scraper-go directory

### No Metrics Files Found
Run load tests first before comparison.