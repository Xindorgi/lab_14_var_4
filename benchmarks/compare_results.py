#!/usr/bin/env python3
"""
Comparison script for Python vs Go scraper performance.
Generates comparison report and visualizations.
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import numpy as np

def load_latest_metrics(scraper_type: str) -> Optional[Dict[str, Any]]:
    """Load the latest metrics file for a scraper type."""
    pattern = f"benchmark_results/{scraper_type}_scraper_metrics_*.json"
    files = glob.glob(pattern)
    
    if not files:
        # Try without timestamp
        pattern = f"benchmark_results/{scraper_type}_scraper_metrics.json"
        files = glob.glob(pattern)
    
    if not files:
        print(f"No metrics files found for {scraper_type} scraper")
        return None
    
    # Get the most recent file
    latest_file = max(files, key=os.path.getctime)
    
    try:
        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading metrics from {latest_file}: {e}")
        return None

def compare_performance(python_metrics: Dict[str, Any], go_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compare performance metrics between Python and Go scrapers."""
    comparison = {
        "comparison_date": datetime.utcnow().isoformat(),
        "python": {},
        "go": {},
        "differences": {},
        "improvement_ratios": {}
    }
    
    if not python_metrics.get("summary") or not go_metrics.get("summary"):
        print("Warning: Missing summary data in metrics")
        return comparison
    
    python_summary = python_metrics["summary"]
    go_summary = go_metrics["summary"]
    
    # Store summaries
    comparison["python"] = python_summary
    comparison["go"] = go_summary
    
    # Calculate differences and improvement ratios
    metrics_to_compare = [
        ("avg_execution_time", "Execution Time (seconds)", True),  # Lower is better
        ("avg_cpu_across_runs", "Average CPU Usage (%)", True),    # Lower is better
        ("avg_max_cpu", "Max CPU Usage (%)", True),                # Lower is better
        ("avg_memory_across_runs", "Average Memory (MB)", True),   # Lower is better
        ("avg_max_memory", "Max Memory (MB)", True)                # Lower is better
    ]
    
    for metric_key, display_name, lower_is_better in metrics_to_compare:
        python_value = python_summary.get(metric_key, 0)
        go_value = go_summary.get(metric_key, 0)
        
        if python_value == 0 or go_value == 0:
            continue
        
        difference = go_value - python_value
        if lower_is_better:
            improvement = python_value / go_value if go_value != 0 else 0
        else:
            improvement = go_value / python_value if python_value != 0 else 0
        
        comparison["differences"][metric_key] = {
            "display_name": display_name,
            "python": python_value,
            "go": go_value,
            "difference": difference,
            "difference_percent": (difference / python_value * 100) if python_value != 0 else 0,
            "improvement_ratio": improvement,
            "lower_is_better": lower_is_better
        }
        
        comparison["improvement_ratios"][metric_key] = improvement
    
    return comparison

def generate_report(comparison: Dict[str, Any]) -> str:
    """Generate a human-readable performance comparison report."""
    report_lines = []
    
    report_lines.append("=" * 70)
    report_lines.append("PERFORMANCE COMPARISON REPORT: Python vs Go News Scraper")
    report_lines.append("=" * 70)
    report_lines.append(f"Comparison Date: {comparison['comparison_date']}")
    report_lines.append("")
    
    # Summary table
    report_lines.append("SUMMARY METRICS")
    report_lines.append("-" * 70)
    report_lines.append(f"{'Metric':<30} {'Python':<15} {'Go':<15} {'Difference':<15}")
    report_lines.append("-" * 70)
    
    for metric_key, diff_info in comparison.get("differences", {}).items():
        python_val = diff_info["python"]
        go_val = diff_info["go"]
        diff = diff_info["difference"]
        
        # Format values based on metric type
        if "time" in metric_key:
            python_fmt = f"{python_val:.2f}s"
            go_fmt = f"{go_val:.2f}s"
            diff_fmt = f"{diff:+.2f}s"
        elif "memory" in metric_key:
            python_fmt = f"{python_val:.1f} MB"
            go_fmt = f"{go_val:.1f} MB"
            diff_fmt = f"{diff:+.1f} MB"
        else:  # CPU percentages
            python_fmt = f"{python_val:.1f}%"
            go_fmt = f"{go_val:.1f}%"
            diff_fmt = f"{diff:+.1f}%"
        
        report_lines.append(f"{diff_info['display_name']:<30} {python_fmt:<15} {go_fmt:<15} {diff_fmt:<15}")
    
    report_lines.append("")
    
    # Improvement analysis
    report_lines.append("IMPROVEMENT ANALYSIS")
    report_lines.append("-" * 70)
    
    for metric_key, diff_info in comparison.get("differences", {}).items():
        improvement = diff_info["improvement_ratio"]
        lower_is_better = diff_info["lower_is_better"]
        
        if lower_is_better:
            if improvement > 1:
                analysis = f"Go is {improvement:.2f}x faster/better than Python"
            elif improvement < 1:
                analysis = f"Python is {1/improvement:.2f}x faster/better than Go"
            else:
                analysis = "Performance is equal"
        else:
            if improvement > 1:
                analysis = f"Go is {improvement:.2f}x better than Python"
            elif improvement < 1:
                analysis = f"Python is {1/improvement:.2f}x better than Go"
            else:
                analysis = "Performance is equal"
        
        report_lines.append(f"{diff_info['display_name']}: {analysis}")
    
    report_lines.append("")
    
    # Overall conclusion
    report_lines.append("OVERALL CONCLUSION")
    report_lines.append("-" * 70)
    
    # Count improvements
    go_improvements = 0
    python_improvements = 0
    equal = 0
    
    for metric_key, diff_info in comparison.get("differences", {}).items():
        improvement = diff_info["improvement_ratio"]
        lower_is_better = diff_info["lower_is_better"]
        
        if lower_is_better:
            if improvement > 1.1:  # 10% threshold for significant improvement
                go_improvements += 1
            elif improvement < 0.9:
                python_improvements += 1
            else:
                equal += 1
    
    if go_improvements > python_improvements:
        conclusion = "Go scraper demonstrates better overall performance"
    elif python_improvements > go_improvements:
        conclusion = "Python scraper demonstrates better overall performance"
    else:
        conclusion = "Both scrapers show comparable performance"
    
    report_lines.append(conclusion)
    report_lines.append(f"Go advantages: {go_improvements} metrics")
    report_lines.append(f"Python advantages: {python_improvements} metrics")
    report_lines.append(f"Comparable metrics: {equal} metrics")
    
    report_lines.append("")
    report_lines.append("=" * 70)
    
    return "\n".join(report_lines)

def create_visualizations(comparison: Dict[str, Any], output_dir: str = "benchmark_results"):
    """Create visualization charts for performance comparison."""
    os.makedirs(output_dir, exist_ok=True)
    
    metrics_to_plot = []
    python_values = []
    go_values = []
    metric_names = []
    
    for metric_key, diff_info in comparison.get("differences", {}).items():
        metrics_to_plot.append(metric_key)
        python_values.append(diff_info["python"])
        go_values.append(diff_info["go"])
        metric_names.append(diff_info["display_name"])
    
    if not metrics_to_plot:
        print("No metrics to visualize")
        return
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    x = np.arange(len(metrics_to_plot))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, python_values, width, label='Python', color='#1f77b4')
    bars2 = ax.bar(x + width/2, go_values, width, label='Go', color='#ff7f0e')
    
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Values')
    ax.set_title('Performance Comparison: Python vs Go Scraper')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_names, rotation=45, ha='right')
    ax.legend()
    
    # Add value labels on bars
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=8)
    
    autolabel(bars1)
    autolabel(bars2)
    
    plt.tight_layout()
    
    # Save the chart
    chart_path = os.path.join(output_dir, "performance_comparison.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    
    print(f"Visualization saved to: {chart_path}")
    
    # Create improvement ratio chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    improvement_ratios = []
    for metric_key in metrics_to_plot:
        ratio = comparison["improvement_ratios"][metric_key]
        improvement_ratios.append(ratio)
    
    colors = ['green' if ratio > 1 else 'red' for ratio in improvement_ratios]
    
    bars = ax.bar(metric_names, improvement_ratios, color=colors)
    ax.axhline(y=1, color='black', linestyle='--', alpha=0.5)
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Improvement Ratio (Go/Python)')
    ax.set_title('Improvement Ratio: Values > 1 indicate Go is better')
    ax.set_xticklabels(metric_names, rotation=45, ha='right')
    
    # Add ratio labels
    for bar, ratio in zip(bars, improvement_ratios):
        height = bar.get_height()
        ax.annotate(f'{ratio:.2f}x',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),
                   textcoords="offset points",
                   ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    ratio_chart_path = os.path.join(output_dir, "improvement_ratios.png")
    plt.savefig(ratio_chart_path, dpi=300)
    plt.close()
    
    print(f"Improvement ratio chart saved to: {ratio_chart_path}")

def main():
    """Main function for comparison analysis."""
    print("Loading performance metrics...")
    
    # Load metrics
    python_metrics = load_latest_metrics("python")
    go_metrics = load_latest_metrics("go")
    
    if not python_metrics or not go_metrics:
        print("Error: Could not load metrics for both scrapers.")
        print("Please run load tests first:")
        print("  python benchmarks/load_test_python.py")
        print("  python benchmarks/load_test_go.py")
        return
    
    # Compare performance
    print("Comparing performance...")
    comparison = compare_performance(python_metrics, go_metrics)
    
    # Generate report
    report = generate_report(comparison)
    print("\n" + report)
    
    # Save report to file
    report_path = "benchmark_results/performance_comparison_report.txt"
    os.makedirs("benchmark_results", exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    
    # Save comparison data as JSON
    json_path = "benchmark_results/performance_comparison.json"
    with open(json_path, "w") as f:
        json.dump(comparison, f, indent=2, default=str)
    
    print(f"Comparison data saved to: {json_path}")
    
    # Create visualizations
    try:
        create_visualizations(comparison)
    except Exception as e:
        print(f"Note: Could not create visualizations: {e}")
        print("Make sure matplotlib is installed: pip install matplotlib")
    
    print("\nComparison completed successfully!")

if __name__ == "__main__":
    main()