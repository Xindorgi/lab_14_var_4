#!/usr/bin/env python3
"""
FastAPI REST server for analyzer metrics and statistics.
Provides HTTP endpoints for dashboard integration.
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config import AppConfig, load_config_from_env
from sliding_window import AnalysisPipeline, WindowStatistics

# Global pipeline instance
_pipeline: Optional[AnalysisPipeline] = None
_pipeline_lock = threading.Lock()
_startup_time = datetime.utcnow()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app"""
    # Startup
    logging.info("Starting analyzer API server")
    
    # Load configuration
    config = load_config_from_env()
    
    # Create pipeline if enabled
    if config.api.enabled:
        global _pipeline
        with _pipeline_lock:
            if _pipeline is None:
                try:
                    _pipeline = AnalysisPipeline(config)
                    # Start pipeline in background thread
                    pipeline_thread = threading.Thread(
                        target=_pipeline.start,
                        daemon=True,
                        name="analysis-pipeline"
                    )
                    pipeline_thread.start()
                    logging.info("Analysis pipeline started in background")
                except Exception as e:
                    logging.error(f"Failed to start analysis pipeline: {e}")
    
    yield
    
    # Shutdown
    logging.info("Shutting down analyzer API server")
    if _pipeline:
        _pipeline.stop()
        logging.info("Analysis pipeline stopped")

# Create FastAPI app
app = FastAPI(
    title="News Analyzer API",
    description="REST API for news analysis pipeline metrics and statistics",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_pipeline() -> AnalysisPipeline:
    """Get the global pipeline instance"""
    if _pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Analysis pipeline not available. Check if API is enabled in configuration."
        )
    return _pipeline

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "News Analyzer API",
        "version": "0.1.0",
        "status": "running",
        "uptime": str(datetime.utcnow() - _startup_time),
        "endpoints": {
            "/": "This information",
            "/health": "Health check",
            "/metrics": "Current metrics",
            "/stats": "Detailed statistics",
            "/history": "Historical statistics",
            "/sources": "Source distribution",
            "/window": "Current window information",
            "/pipeline": "Pipeline status",
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        pipeline = get_pipeline()
        # Check if pipeline is running
        # (simplified check - in real implementation, verify components)
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "pipeline": "running",
                "api": "running"
            }
        }
    except HTTPException:
        return {
            "status": "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "pipeline": "not_available",
                "api": "running"
            }
        }

@app.get("/metrics")
async def get_metrics():
    """Get current metrics (simplified for dashboard)"""
    try:
        pipeline = get_pipeline()
        processor = pipeline.processor
        
        # Get current window articles
        window_articles = processor.get_current_window()
        
        # Calculate basic metrics
        total_articles = len(window_articles)
        
        # Articles per source
        sources = {}
        for article in window_articles:
            source = article.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        # Calculate publishing rate (articles per minute)
        window_duration_minutes = processor.window_size.total_seconds() / 60
        publishing_rate = total_articles / window_duration_minutes if window_duration_minutes > 0 else 0
        
        # Calculate average title length
        title_lengths = [len(article.get('title', '')) for article in window_articles]
        avg_title_length = sum(title_lengths) / len(title_lengths) if title_lengths else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "window_start": (datetime.utcnow() - processor.window_size).isoformat(),
            "window_end": datetime.utcnow().isoformat(),
            "total_articles": total_articles,
            "sources_count": len(sources),
            "publishing_rate": round(publishing_rate, 2),
            "avg_title_length": round(avg_title_length, 2),
            "articles_per_source": sources,
        }
    except Exception as e:
        logging.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get detailed statistics from the current window"""
    try:
        pipeline = get_pipeline()
        processor = pipeline.processor
        
        # Process window to get statistics
        statistics = processor.process_window()
        
        # Convert to dictionary
        stats_dict = statistics.to_dict()
        
        # Add pipeline info
        stats_dict.update({
            "pipeline": {
                "total_articles_processed": pipeline.total_articles,
                "windows_processed": processor.processed_windows,
                "dropped_articles": processor.dropped_articles,
            }
        })
        
        return stats_dict
    except Exception as e:
        logging.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(hours: int = 24, limit: int = 100):
    """Get historical statistics (mock for now)"""
    # Note: In a real implementation, this would query a database
    # For now, generate mock historical data
    
    now = datetime.utcnow()
    history = []
    
    for i in range(min(limit, hours * 12)):  # 5-minute windows
        window_start = now - timedelta(minutes=(i + 1) * 5)
        window_end = window_start + timedelta(minutes=5)
        
        # Generate mock data
        import random
        history.append({
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "total_articles": random.randint(10, 100),
            "sources_count": random.randint(1, 5),
            "publishing_rate": round(random.uniform(0.5, 5.0), 2),
            "articles_per_source": {
                f"Source_{j}": random.randint(1, 30)
                for j in range(random.randint(1, 5))
            }
        })
    
    return {
        "query": {
            "hours": hours,
            "limit": limit,
            "actual_results": len(history)
        },
        "history": history
    }

@app.get("/sources")
async def get_sources():
    """Get source distribution statistics"""
    try:
        pipeline = get_pipeline()
        processor = pipeline.processor
        
        window_articles = processor.get_current_window()
        
        # Calculate source distribution
        sources = {}
        for article in window_articles:
            source = article.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        # Sort by count
        sorted_sources = dict(sorted(sources.items(), key=lambda x: x[1], reverse=True))
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_sources": len(sorted_sources),
            "sources": sorted_sources,
            "top_source": max(sources.items(), key=lambda x: x[1])[0] if sources else None,
        }
    except Exception as e:
        logging.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/window")
async def get_window():
    """Get current window information"""
    try:
        pipeline = get_pipeline()
        processor = pipeline.processor
        
        window_articles = processor.get_current_window()
        
        return {
            "window_size_minutes": processor.window_size.total_seconds() / 60,
            "slide_interval_minutes": processor.slide_interval.total_seconds() / 60,
            "articles_in_window": len(window_articles),
            "window_start": (datetime.utcnow() - processor.window_size).isoformat(),
            "window_end": datetime.utcnow().isoformat(),
            "max_articles": processor.max_articles,
            "processing_active": processor.processing,
        }
    except Exception as e:
        logging.error(f"Error getting window info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pipeline")
async def get_pipeline_status():
    """Get pipeline status and metrics"""
    try:
        pipeline = get_pipeline()
        
        return {
            "status": "running",
            "total_articles": pipeline.total_articles,
            "processor": {
                "windows_processed": pipeline.processor.processed_windows,
                "dropped_articles": pipeline.processor.dropped_articles,
                "processing_active": pipeline.processor.processing,
            },
            "consumer": {
                "type": pipeline.config.broker.broker_type.value,
                "enabled": pipeline.config.broker.enabled,
            },
            "uptime": str(datetime.utcnow() - _startup_time),
        }
    except Exception as e:
        logging.error(f"Error getting pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refresh")
async def refresh_window():
    """Manually trigger window processing"""
    try:
        pipeline = get_pipeline()
        processor = pipeline.processor
        
        statistics = processor.process_window()
        
        return {
            "status": "success",
            "message": "Window processed successfully",
            "statistics": statistics.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logging.error(f"Error refreshing window: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def start_api_server(config: AppConfig):
    """Start the FastAPI server"""
    if not config.api.enabled:
        logging.info("API server is disabled in configuration")
        return
    
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format
    )
    
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level=config.logging.level.lower()
    )

def main():
    """Main function to run the API server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="News Analyzer API Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config_from_env()
    
    # Override with command line arguments
    config.api.host = args.host
    config.api.port = args.port
    
    # Start server
    if args.reload:
        uvicorn.run(
            "api:app",
            host=config.api.host,
            port=config.api.port,
            reload=True,
            log_level=config.logging.level.lower()
        )
    else:
        start_api_server(config)

if __name__ == "__main__":
    main()