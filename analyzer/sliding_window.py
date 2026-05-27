#!/usr/bin/env python3
"""
Sliding window processor for news articles.
Processes articles in 5-minute sliding windows with 1-minute intervals.
"""

import json
import logging
import threading
import time
import heapq
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import statistics

from config import AppConfig, load_config_from_env
from consumer import ConsumerFactory, MessageConsumer

@dataclass
class WindowStatistics:
    """Statistics for a time window"""
    window_start: datetime
    window_end: datetime
    total_articles: int
    articles_per_source: Dict[str, int]
    avg_title_length: float
    avg_description_length: float
    sources: List[str]
    categories: Dict[str, int]
    publishing_frequency: float  # articles per minute
    top_keywords: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "total_articles": self.total_articles,
            "articles_per_source": self.articles_per_source,
            "avg_title_length": round(self.avg_title_length, 2),
            "avg_description_length": round(self.avg_description_length, 2),
            "sources": self.sources,
            "categories": self.categories,
            "publishing_frequency": round(self.publishing_frequency, 2),
            "top_keywords": self.top_keywords,
        }

class SlidingWindowProcessor:
    """Manages sliding time windows for article processing"""
    
    def __init__(self, config: AppConfig):
        self.config = config.analysis
        self.logger = self._setup_logging()
        
        # Window configuration
        self.window_size = timedelta(minutes=config.window_size_minutes)
        self.slide_interval = timedelta(minutes=config.sliding_interval_minutes)
        self.max_articles = config.max_articles_per_window
        
        # Data structures
        self.articles = deque()  # (timestamp, article) tuples
        self.window_lock = threading.Lock()
        
        # Processing thread
        self.processing = False
        self.processing_thread = None
        
        # Callbacks
        self.window_callback = None
        
        # Statistics
        self.processed_windows = 0
        self.dropped_articles = 0
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def add_article(self, article: Dict[str, Any]):
        """Add an article to the processor"""
        try:
            # Parse timestamp (use scraped_at if available, otherwise current time)
            if 'scraped_at' in article:
                timestamp = datetime.fromisoformat(article['scraped_at'].replace('Z', '+00:00'))
            elif 'published' in article:
                # Try to parse published date
                try:
                    timestamp = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()
            
            with self.window_lock:
                # Add article with timestamp
                self.articles.append((timestamp, article))
                
                # Remove old articles outside of current window
                cutoff_time = datetime.utcnow() - self.window_size
                while self.articles and self.articles[0][0] < cutoff_time:
                    self.articles.popleft()
                
                # Limit total articles
                while len(self.articles) > self.max_articles:
                    self.articles.popleft()
                    self.dropped_articles += 1
                
                if len(self.articles) % 10 == 0:
                    self.logger.debug(f"Window contains {len(self.articles)} articles")
        
        except Exception as e:
            self.logger.error(f"Error adding article: {e}")
    
    def get_current_window(self) -> List[Dict[str, Any]]:
        """Get articles in the current time window"""
        cutoff_time = datetime.utcnow() - self.window_size
        
        with self.window_lock:
            # Filter articles within window
            window_articles = []
            for timestamp, article in self.articles:
                if timestamp >= cutoff_time:
                    window_articles.append(article)
            
            return window_articles
    
    def calculate_statistics(self, articles: List[Dict[str, Any]]) -> WindowStatistics:
        """Calculate statistics for a window of articles"""
        if not articles:
            # Return empty statistics
            return WindowStatistics(
                window_start=datetime.utcnow() - self.window_size,
                window_end=datetime.utcnow(),
                total_articles=0,
                articles_per_source={},
                avg_title_length=0,
                avg_description_length=0,
                sources=[],
                categories={},
                publishing_frequency=0,
                top_keywords=[]
            )
        
        # Basic counts
        total_articles = len(articles)
        
        # Articles per source
        articles_per_source = defaultdict(int)
        sources = set()
        
        # Text analysis
        title_lengths = []
        description_lengths = []
        
        # Categories
        categories = defaultdict(int)
        
        # Keywords (simplified - just use words from titles)
        word_freq = defaultdict(int)
        
        for article in articles:
            # Source statistics
            source = article.get('source', 'unknown')
            articles_per_source[source] += 1
            sources.add(source)
            
            # Title length
            title = article.get('title', '')
            title_lengths.append(len(title))
            
            # Description length
            description = article.get('description', '')
            description_lengths.append(len(description))
            
            # Categories
            for category in article.get('categories', []):
                if isinstance(category, dict):
                    category_name = category.get('term', str(category))
                else:
                    category_name = str(category)
                categories[category_name] += 1
            
            # Simple keyword extraction (split title into words)
            words = title.lower().split()
            for word in words:
                if len(word) > 3:  # Ignore short words
                    word_freq[word] += 1
        
        # Calculate averages
        avg_title_length = statistics.mean(title_lengths) if title_lengths else 0
        avg_description_length = statistics.mean(description_lengths) if description_lengths else 0
        
        # Publishing frequency (articles per minute)
        window_duration_minutes = self.window_size.total_seconds() / 60
        publishing_frequency = total_articles / window_duration_minutes if window_duration_minutes > 0 else 0
        
        # Top keywords
        top_keywords = []
        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            top_keywords.append({"word": word, "frequency": freq})
        
        return WindowStatistics(
            window_start=datetime.utcnow() - self.window_size,
            window_end=datetime.utcnow(),
            total_articles=total_articles,
            articles_per_source=dict(articles_per_source),
            avg_title_length=avg_title_length,
            avg_description_length=avg_description_length,
            sources=list(sources),
            categories=dict(categories),
            publishing_frequency=publishing_frequency,
            top_keywords=top_keywords
        )
    
    def process_window(self):
        """Process the current window and trigger callback"""
        window_articles = self.get_current_window()
        statistics = self.calculate_statistics(window_articles)
        
        self.logger.info(
            f"Window processed: {statistics.total_articles} articles, "
            f"{len(statistics.sources)} sources, "
            f"{statistics.publishing_frequency:.1f} articles/min"
        )
        
        # Trigger callback if set
        if self.window_callback:
            try:
                self.window_callback(statistics)
            except Exception as e:
                self.logger.error(f"Error in window callback: {e}")
        
        self.processed_windows += 1
        
        # Return statistics for further processing
        return statistics
    
    def start_processing(self):
        """Start periodic window processing"""
        self.processing = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        self.logger.info(f"Started sliding window processor (window: {self.window_size}, slide: {self.slide_interval})")
    
    def _processing_loop(self):
        """Main processing loop"""
        while self.processing:
            try:
                self.process_window()
                time.sleep(self.slide_interval.total_seconds())
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                time.sleep(1)  # Brief pause on error
    
    def stop_processing(self):
        """Stop window processing"""
        self.processing = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        self.logger.info(f"Stopped sliding window processor. Processed {self.processed_windows} windows.")
    
    def set_window_callback(self, callback: Callable[[WindowStatistics], None]):
        """Set callback for processed windows"""
        self.window_callback = callback

class AnalysisPipeline:
    """Complete analysis pipeline combining consumer and window processor"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = self._setup_logging()
        
        # Create consumer
        self.consumer = ConsumerFactory.create_consumer(config)
        self.consumer.set_message_callback(self._handle_message)
        
        # Create window processor
        self.processor = SlidingWindowProcessor(config)
        self.processor.set_window_callback(self._handle_window)
        
        # Storage (optional)
        self.storage = None
        if config.database.enabled:
            self._setup_database()
        
        # Statistics
        self.total_articles = 0
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _setup_database(self):
        """Setup database connection"""
        try:
            # Import here to avoid dependency if not used
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(
                host=self.config.database.host,
                port=self.config.database.port,
                database=self.config.database.database,
                user=self.config.database.username,
                password=self.config.database.password
            )
            self.storage = conn
            self.logger.info("Connected to database")
            
        except ImportError:
            self.logger.warning("psycopg2 not installed, database disabled")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
    
    def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from consumer"""
        self.total_articles += 1
        self.processor.add_article(message)
        
        if self.total_articles % 10 == 0:
            self.logger.info(f"Processed {self.total_articles} articles")
    
    def _handle_window(self, statistics: WindowStatistics):
        """Handle processed window statistics"""
        # Log statistics
        stats_dict = statistics.to_dict()
        self.logger.info(f"Window statistics: {json.dumps(stats_dict, indent=2)}")
        
        # Store in database if available
        if self.storage:
            self._store_statistics(statistics)
    
    def _store_statistics(self, statistics: WindowStatistics):
        """Store statistics in database"""
        try:
            cursor = self.storage.cursor()
            cursor.execute("""
                INSERT INTO analysis_results 
                (window_start, window_end, analysis_type, results)
                VALUES (%s, %s, %s, %s)
            """, (
                statistics.window_start,
                statistics.window_end,
                'sliding_window',
                json.dumps(statistics.to_dict())
            ))
            self.storage.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Failed to store statistics: {e}")
    
    def start(self):
        """Start the analysis pipeline"""
        self.logger.info("Starting analysis pipeline...")
        
        # Start window processor
        self.processor.start_processing()
        
        # Start consumer (this will block)
        self.consumer.start()
    
    def stop(self):
        """Stop the analysis pipeline"""
        self.logger.info("Stopping analysis pipeline...")
        self.processor.stop_processing()
        self.consumer.stop()
        
        if self.storage:
            self.storage.close()

def main():
    """Main function for sliding window processor"""
    import signal
    import sys
    
    # Load configuration
    config = load_config_from_env()
    
    # Create pipeline
    pipeline = AnalysisPipeline(config)
    
    # Setup signal handling
    def signal_handler(sig, frame):
        print("\nShutting down pipeline...")
        pipeline.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 80)
    print("Sliding Window Analysis Pipeline")
    print("=" * 80)
    print(f"Window size: {config.analysis.window_size_minutes} minutes")
    print(f"Slide interval: {config.analysis.sliding_interval_minutes} minutes")
    print(f"Max articles per window: {config.analysis.max_articles_per_window}")
    print(f"Broker: {config.broker.broker_type.value}")
    print("=" * 80)
    
    try:
        # Start pipeline
        pipeline.start()
    except KeyboardInterrupt:
        pipeline.stop()
    except Exception as e:
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        pipeline.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()