#!/usr/bin/env python3
"""
Apache Arrow Flight client for fetching aggregated data from Go scraper.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# Try to import Arrow Flight (optional)
try:
    import pyarrow as pa
    import pyarrow.flight as flight
    ARROW_AVAILABLE = True
except ImportError:
    ARROW_AVAILABLE = False
    print("Warning: pyarrow not installed. Arrow Flight support disabled.")
    print("Install with: pip install pyarrow")

from config import AppConfig, load_config_from_env

class ArrowFlightClient:
    """Client for Apache Arrow Flight server"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.client = None
        self.host = "localhost"
        self.port = 8815
        
        if not ARROW_AVAILABLE:
            self.logger.warning("Arrow Flight not available (pyarrow not installed)")
            return
        
        try:
            # Create Flight client
            location = flight.Location.for_grpc_tcp(self.host, self.port)
            self.client = flight.FlightClient(location)
            self.logger.info(f"Connected to Arrow Flight server at {self.host}:{self.port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Arrow Flight server: {e}")
            self.client = None
    
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
    
    def is_available(self) -> bool:
        """Check if Arrow Flight client is available"""
        return ARROW_AVAILABLE and self.client is not None
    
    def get_aggregated_stats(self, window_start: Optional[datetime] = None, 
                            window_end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch aggregated statistics from Arrow Flight server"""
        if not self.is_available():
            self.logger.warning("Arrow Flight client not available")
            return []
        
        try:
            # Create ticket for requested data
            ticket_info = {
                "action": "get_aggregated_stats",
                "window_start": window_start.isoformat() if window_start else None,
                "window_end": window_end.isoformat() if window_end else None,
            }
            
            ticket = flight.Ticket(json.dumps(ticket_info).encode())
            
            # Get Flight info
            flight_info = self.client.get_flight_info(ticket)
            self.logger.info(f"Flight info: {flight_info}")
            
            # Read data
            reader = self.client.do_get(ticket)
            table = reader.read_all()
            
            # Convert to list of dictionaries
            stats = self._table_to_stats(table)
            self.logger.info(f"Retrieved {len(stats)} aggregated statistics")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error fetching aggregated stats: {e}")
            return []
    
    def _table_to_stats(self, table) -> List[Dict[str, Any]]:
        """Convert Arrow table to list of statistics dictionaries"""
        if not ARROW_AVAILABLE:
            return []
        
        try:
            # Convert to pandas DataFrame (if available)
            try:
                import pandas as pd
                df = table.to_pandas()
                stats = df.to_dict('records')
                return stats
            except ImportError:
                # Fall back to manual conversion
                pass
            
            # Manual conversion from Arrow table
            stats = []
            for batch in table.to_batches():
                # This is simplified - real implementation would parse schema
                self.logger.debug(f"Processing batch with {batch.num_rows} rows")
                
                # Convert to dictionary (simplified)
                for i in range(batch.num_rows):
                    stat = {
                        "batch_index": i,
                        "num_rows": batch.num_rows,
                        "schema": str(batch.schema),
                    }
                    stats.append(stat)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error converting Arrow table: {e}")
            return []
    
    def list_available_windows(self) -> List[Dict[str, Any]]:
        """List available aggregation windows"""
        if not self.is_available():
            self.logger.warning("Arrow Flight client not available")
            return []
        
        try:
            # Use DoAction to list windows
            action = flight.Action("list_windows", b"")
            results = list(self.client.do_action(action))
            
            windows = []
            for result in results:
                try:
                    window_info = json.loads(result.body.to_pybytes().decode())
                    windows.append(window_info)
                except:
                    pass
            
            return windows
            
        except Exception as e:
            self.logger.error(f"Error listing windows: {e}")
            return []
    
    def get_schema(self) -> Optional[Dict[str, Any]]:
        """Get Arrow schema information"""
        if not self.is_available():
            return None
        
        try:
            # Get schema for aggregated stats
            ticket_info = {"action": "get_schema"}
            ticket = flight.Ticket(json.dumps(ticket_info).encode())
            
            flight_info = self.client.get_flight_info(ticket)
            schema = flight_info.schema
            
            if schema:
                return {
                    "schema": str(schema),
                    "fields": [{"name": field.name, "type": str(field.type)} 
                              for field in schema],
                }
            
        except Exception as e:
            self.logger.error(f"Error getting schema: {e}")
        
        return None
    
    def health_check(self) -> bool:
        """Check if Arrow Flight server is healthy"""
        if not self.is_available():
            return False
        
        try:
            # Simple action to check health
            action = flight.Action("health", b"")
            results = list(self.client.do_action(action))
            return len(results) > 0
        except:
            return False
    
    def close(self):
        """Close the client connection"""
        if self.client:
            self.client.close()
            self.logger.info("Arrow Flight client closed")

class MockArrowFlightClient:
    """Mock client for when Arrow Flight is not available"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(__name__ + ".mock")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def is_available(self) -> bool:
        return False
    
    def get_aggregated_stats(self, window_start=None, window_end=None):
        self.logger.warning("Using mock Arrow Flight client - no real data available")
        
        # Return mock data for testing
        return [
            {
                "window_start": (window_start or datetime.utcnow()).isoformat(),
                "window_end": (window_end or datetime.utcnow()).isoformat(),
                "total_articles": 42,
                "articles_by_source": {"Lenta.ru": 20, "Interfax": 15, "RIA": 7},
                "publishing_rate": 0.7,
                "avg_title_length": 45.2,
                "source": "mock_arrow_client",
            }
        ]
    
    def list_available_windows(self):
        return [
            {
                "window_start": datetime.utcnow().isoformat(),
                "window_end": datetime.utcnow().isoformat(),
                "article_count": 42,
            }
        ]
    
    def get_schema(self):
        return {
            "schema": "mock_schema",
            "fields": [
                {"name": "window_start", "type": "timestamp"},
                {"name": "window_end", "type": "timestamp"},
                {"name": "total_articles", "type": "int32"},
            ]
        }
    
    def health_check(self):
        return False
    
    def close(self):
        pass

def create_arrow_client(config: AppConfig):
    """Create appropriate Arrow Flight client based on availability"""
    if ARROW_AVAILABLE and config.arrow_flight_enabled:
        client = ArrowFlightClient(config)
        if client.is_available():
            return client
    
    # Fall back to mock client
    return MockArrowFlightClient(config)

def main():
    """Test Arrow Flight client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Arrow Flight Client Test")
    parser.add_argument("--host", default="localhost", help="Arrow Flight server host")
    parser.add_argument("--port", type=int, default=8815, help="Arrow Flight server port")
    parser.add_argument("--list-windows", action="store_true", help="List available windows")
    parser.add_argument("--get-stats", action="store_true", help="Get aggregated statistics")
    parser.add_argument("--get-schema", action="store_true", help="Get schema information")
    parser.add_argument("--health", action="store_true", help="Check server health")
    
    args = parser.parse_args()
    
    # Create config
    config = load_config_from_env()
    
    # Create client
    client = create_arrow_client(config)
    
    if args.health:
        print(f"Server health: {'OK' if client.health_check() else 'FAILED'}")
    
    if args.list_windows:
        windows = client.list_available_windows()
        print(f"Available windows ({len(windows)}):")
        for window in windows:
            print(f"  - {window}")
    
    if args.get_schema:
        schema = client.get_schema()
        if schema:
            print("Schema:")
            print(json.dumps(schema, indent=2))
        else:
            print("No schema available")
    
    if args.get_stats:
        stats = client.get_aggregated_stats()
        print(f"Aggregated statistics ({len(stats)}):")
        for stat in stats[:3]:  # Show first 3
            print(json.dumps(stat, indent=2))
    
    client.close()

if __name__ == "__main__":
    main()