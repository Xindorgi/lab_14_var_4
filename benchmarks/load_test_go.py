#!/usr/bin/env python3
"""
Load testing script for Go news scraper.
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

def compile_go_scraper() -> str:
    """Compile Go scraper and return path to binary."""
    scraper_dir = os.path.join(os.path.dirname(__file__), "..", "scraper-go")
    binary_path = os.path.join(scraper_dir, "news-scraper")
    
    # Check if binary already exists and is recent
    if os.path.exists(binary_path):
        source_mtime = max(
            os.path.getmtime(os.path.join(scraper_dir, "main.go")),
            os.path.getmtime(os.path.join(scraper_dir, "config.go"))
        )
        binary_mtime = os.path.getmtime(binary_path)
        
        if binary_mtime > source_mtime:
            print(f"Using existing binary: {binary_path}")
            return binary_path
    
    # Compile the binary
    print(f"Compiling Go scraper...")
    compile_cmd = ["go", "build", "-o", binary_path, "main.go"]
    
    try:
        result = subprocess.run(
            compile_cmd,
            cwd=scraper_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"Compilation failed:\n{result.stderr}")
            # Try to run with go run as fallback
            return None
        else:
            print(f"Binary compiled successfully: {binary_path}")
            return binary_path
    except subprocess.TimeoutExpired:
        print("Compilation timeout")
        return None
    except Exception as e:
        print(f"Compilation error: {e}")
        return None

def run_go_scraper(binary_path: str, iterations: int = 3) -> Dict[str, Any]:
    """Run Go scraper multiple times and collect metrics."""
    print(f"Starting Go scraper load test ({iterations} iterations)")
    
    metrics = {
        "scraper": "go",
        "iterations": iterations,
        "runs": [],
        "summary": {}
    }
    
    scraper_dir = os.path.dirname(binary_path)
    
    for i in range(iterations):
        print(f"\n--- Iteration {i+1}/{iterations} ---")
        
        # Start the scraper process
        start_time = time.time()
        process = subprocess.Popen(
            [binary_path],
            cwd=scraper_dir,
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
        
        # Print any errors
        if stderr:
            print(f"  Stderr: {stderr[:200]}...")
    
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

def save_metrics(metrics: Dict[str, Any], filename: str = "go_scraper_metrics.json"):
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
    print("Go Scraper Load Test")
    print("=" * 60)
    
    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("Error: psutil module is required for load testing.")
        print("Install it with: pip install psutil")
        sys.exit(1)
    
    # Compile or find Go binary
    binary_path = compile_go_scraper()
    if not binary_path:
        print("Warning: Could not compile Go scraper. Trying to use 'go run' as fallback.")
        # We'll handle this differently - maybe run directly with go run
        # For now, exit
        sys.exit(1)
    
    # Run load test
    try:
        metrics = run_go_scraper(binary_path, iterations=3)
        
        # Save results
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"go_scraper_metrics_{timestamp}.json"
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