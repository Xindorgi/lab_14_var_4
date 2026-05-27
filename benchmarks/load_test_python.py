#!/usr/bin/env python3
"""
Load testing script for Python news scraper.
Measures execution time, CPU and RAM consumption.
"""

import subprocess
import time
import json
import psutil
import os
import sys
from datetime import datetime
from typing import Dict, Any

def get_process_memory_usage(pid: int) -> float:
    """Get memory usage in MB for a process."""
    try:
        process = psutil.Process(pid)
        memory_info = process.memory_info()
        return memory_info.rss / 1024 / 1024  # Convert to MB
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0

def get_process_cpu_usage(pid: int, interval: float = 0.1) -> float:
    """Get CPU usage percentage for a process."""
    try:
        process = psutil.Process(pid)
        return process.cpu_percent(interval=interval)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0

def run_python_scraper(iterations: int = 3) -> Dict[str, Any]:
    """Run Python scraper multiple times and collect metrics."""
    print(f"Starting Python scraper load test ({iterations} iterations)")
    
    metrics = {
        "scraper": "python",
        "iterations": iterations,
        "runs": [],
        "summary": {}
    }
    
    scraper_path = os.path.join(os.path.dirname(__file__), "..", "scraper-python", "main.py")
    
    for i in range(iterations):
        print(f"\n--- Iteration {i+1}/{iterations} ---")
        
        # Start the scraper process
        start_time = time.time()
        process = subprocess.Popen(
            [sys.executable, scraper_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Monitor process while it's running
        cpu_usages = []
        memory_usages = []
        
        while process.poll() is None:
            cpu = get_process_cpu_usage(process.pid, 0.1)
            memory = get_process_memory_usage(process.pid)
            
            if cpu > 0:
                cpu_usages.append(cpu)
            if memory > 0:
                memory_usages.append(memory)
            
            time.sleep(0.2)  # Sample every 200ms
        
        # Get final output
        stdout, stderr = process.communicate()
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Calculate metrics
        avg_cpu = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0
        max_cpu = max(cpu_usages) if cpu_usages else 0
        avg_memory = sum(memory_usages) / len(memory_usages) if memory_usages else 0
        max_memory = max(memory_usages) if memory_usages else 0
        
        run_metrics = {
            "iteration": i + 1,
            "execution_time_seconds": round(execution_time, 2),
            "avg_cpu_percent": round(avg_cpu, 1),
            "max_cpu_percent": round(max_cpu, 1),
            "avg_memory_mb": round(avg_memory, 2),
            "max_memory_mb": round(max_memory, 2),
            "exit_code": process.returncode,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        metrics["runs"].append(run_metrics)
        
        print(f"  Execution time: {execution_time:.2f}s")
        print(f"  Avg CPU: {avg_cpu:.1f}%")
        print(f"  Max CPU: {max_cpu:.1f}%")
        print(f"  Avg Memory: {avg_memory:.2f} MB")
        print(f"  Max Memory: {max_memory:.2f} MB")
        print(f"  Exit code: {process.returncode}")
    
    # Calculate summary statistics
    if metrics["runs"]:
        execution_times = [r["execution_time_seconds"] for r in metrics["runs"]]
        avg_cpus = [r["avg_cpu_percent"] for r in metrics["runs"]]
        max_cpus = [r["max_cpu_percent"] for r in metrics["runs"]]
        avg_memories = [r["avg_memory_mb"] for r in metrics["runs"]]
        max_memories = [r["max_memory_mb"] for r in metrics["runs"]]
        
        metrics["summary"] = {
            "avg_execution_time": round(sum(execution_times) / len(execution_times), 2),
            "min_execution_time": round(min(execution_times), 2),
            "max_execution_time": round(max(execution_times), 2),
            "avg_cpu_across_runs": round(sum(avg_cpus) / len(avg_cpus), 1),
            "avg_max_cpu": round(sum(max_cpus) / len(max_cpus), 1),
            "avg_memory_across_runs": round(sum(avg_memories) / len(avg_memories), 2),
            "avg_max_memory": round(sum(max_memories) / len(max_memories), 2),
            "total_test_duration": round(time.time() - metrics["runs"][0]["timestamp"], 2)
        }
    
    return metrics

def save_metrics(metrics: Dict[str, Any], filename: str = "python_scraper_metrics.json"):
    """Save metrics to JSON file."""
    output_dir = "benchmark_results"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    
    print(f"\nMetrics saved to: {output_path}")
    return output_path

def main():
    """Main function for load testing."""
    print("=" * 60)
    print("Python Scraper Load Test")
    print("=" * 60)
    
    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("Error: psutil module is required for load testing.")
        print("Install it with: pip install psutil")
        sys.exit(1)
    
    # Run load test
    try:
        metrics = run_python_scraper(iterations=3)
        
        # Save results
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"python_scraper_metrics_{timestamp}.json"
        output_path = save_metrics(metrics, filename)
        
        # Print summary
        print("\n" + "=" * 60)
        print("LOAD TEST SUMMARY")
        print("=" * 60)
        if metrics["summary"]:
            summary = metrics["summary"]
            print(f"Average execution time: {summary['avg_execution_time']}s")
            print(f"Execution time range: {summary['min_execution_time']}s - {summary['max_execution_time']}s")
            print(f"Average CPU usage: {summary['avg_cpu_across_runs']}%")
            print(f"Average max CPU: {summary['avg_max_cpu']}%")
            print(f"Average memory usage: {summary['avg_memory_across_runs']} MB")
            print(f"Average max memory: {summary['avg_max_memory']} MB")
        
        print(f"\nDetailed metrics saved to: {output_path}")
        
    except Exception as e:
        print(f"Error during load testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()