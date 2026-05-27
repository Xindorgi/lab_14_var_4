#!/usr/bin/env python3
"""
Consumer for reading news articles from message brokers (Kafka/NATS).
"""

import json
import logging
import signal
import sys
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import asdict
from datetime import datetime

from config import AppConfig, BrokerType, load_config_from_env

# Try to import broker libraries
try:
    from confluent_kafka import Consumer, KafkaError, KafkaException
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: confluent-kafka not installed. Kafka support disabled.")

try:
    import nats
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    print("Warning: nats-py not installed. NATS support disabled.")

class MessageConsumer:
    """Base class for message consumers"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.running = False
        self.message_callback = None
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        
        if self.config.logging.file:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.config.logging.file,
                maxBytes=self.config.logging.max_bytes,
                backupCount=self.config.logging.backup_count
            )
            file_handler.setFormatter(logging.Formatter(self.config.logging.format))
            logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(self.config.logging.format))
        logger.addHandler(console_handler)
        
        logger.setLevel(getattr(logging, self.config.logging.level))
        return logger
    
    def set_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for processing messages"""
        self.message_callback = callback
    
    def start(self):
        """Start the consumer"""
        raise NotImplementedError
    
    def stop(self):
        """Stop the consumer"""
        self.running = False
    
    def process_message(self, message: Dict[str, Any]):
        """Process a single message"""
        if self.message_callback:
            try:
                self.message_callback(message)
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
        else:
            self.logger.warning("No message callback set")

class KafkaConsumer(MessageConsumer):
    """Kafka message consumer"""
    
    def __init__(self, config: AppConfig):
        if not KAFKA_AVAILABLE:
            raise ImportError("confluent-kafka library not available")
        
        super().__init__(config)
        
        # Kafka consumer configuration
        kafka_config = {
            'bootstrap.servers': ','.join(config.broker.bootstrap_servers),
            'group.id': config.broker.group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'session.timeout.ms': 30000,
            'max.poll.interval.ms': 300000,
        }
        
        self.consumer = Consumer(kafka_config)
        self.topics = [config.broker.topic]
    
    def start(self):
        """Start consuming messages from Kafka"""
        self.logger.info(f"Starting Kafka consumer for topics: {self.topics}")
        self.consumer.subscribe(self.topics)
        self.running = True
        
        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition event
                        self.logger.debug(f"Reached end of partition {msg.partition()}")
                    else:
                        self.logger.error(f"Kafka error: {msg.error()}")
                    continue
                
                # Process message
                try:
                    message_data = json.loads(msg.value().decode('utf-8'))
                    message_data['_kafka_metadata'] = {
                        'topic': msg.topic(),
                        'partition': msg.partition(),
                        'offset': msg.offset(),
                        'timestamp': msg.timestamp(),
                    }
                    
                    self.logger.debug(f"Received message from {msg.topic()}[{msg.partition()}]@{msg.offset()}")
                    self.process_message(message_data)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to decode JSON message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing Kafka message: {e}")
        
        except KeyboardInterrupt:
            self.logger.info("Consumer interrupted by user")
        except Exception as e:
            self.logger.error(f"Consumer error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the Kafka consumer"""
        super().stop()
        if hasattr(self, 'consumer'):
            self.consumer.close()
            self.logger.info("Kafka consumer stopped")

class NATSConsumer(MessageConsumer):
    """NATS message consumer"""
    
    def __init__(self, config: AppConfig):
        if not NATS_AVAILABLE:
            raise ImportError("nats-py library not available")
        
        super().__init__(config)
        
        self.nats_url = config.broker.nats_url
        self.subject = config.broker.subject
        self.nc = None
        self.subscription = None
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            message_data = json.loads(msg.data.decode('utf-8'))
            message_data['_nats_metadata'] = {
                'subject': msg.subject,
                'reply': msg.reply,
                'timestamp': datetime.utcnow().isoformat(),
            }
            
            self.logger.debug(f"Received message from {msg.subject}")
            self.process_message(message_data)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing NATS message: {e}")
    
    def start(self):
        """Start consuming messages from NATS"""
        import asyncio
        
        async def run_consumer():
            self.logger.info(f"Starting NATS consumer for subject: {self.subject}")
            
            try:
                # Connect to NATS server
                self.nc = await nats.connect(self.nats_url)
                self.logger.info(f"Connected to NATS server at {self.nats_url}")
                
                # Subscribe to subject
                self.subscription = await self.nc.subscribe(
                    self.subject,
                    cb=self.message_handler
                )
                self.logger.info(f"Subscribed to {self.subject}")
                
                # Keep running
                self.running = True
                while self.running:
                    await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"NATS consumer error: {e}")
            finally:
                await self.stop()
        
        # Run async consumer
        asyncio.run(run_consumer())
    
    async def stop(self):
        """Stop the NATS consumer"""
        super().stop()
        
        if self.subscription:
            await self.subscription.unsubscribe()
            self.subscription = None
        
        if self.nc:
            await self.nc.close()
            self.nc = None
        
        self.logger.info("NATS consumer stopped")

class ConsumerFactory:
    """Factory for creating message consumers"""
    
    @staticmethod
    def create_consumer(config: AppConfig) -> MessageConsumer:
        """Create appropriate consumer based on configuration"""
        if not config.broker.enabled:
            raise ValueError("Broker is not enabled in configuration")
        
        if config.broker.broker_type == BrokerType.KAFKA:
            if not KAFKA_AVAILABLE:
                raise ImportError("Kafka library not available. Install with: pip install confluent-kafka")
            return KafkaConsumer(config)
        
        elif config.broker.broker_type == BrokerType.NATS:
            if not NATS_AVAILABLE:
                raise ImportError("NATS library not available. Install with: pip install nats-py")
            return NATSConsumer(config)
        
        else:
            raise ValueError(f"Unsupported broker type: {config.broker.broker_type}")

def simple_message_printer(message: Dict[str, Any]):
    """Simple callback function that prints messages"""
    print(f"Received article: {message.get('title', 'No title')}")
    print(f"  Source: {message.get('source')}")
    print(f"  Published: {message.get('published')}")
    print(f"  Link: {message.get('link')}")
    print("-" * 80)

def main():
    """Main function for testing the consumer"""
    # Load configuration
    config = load_config_from_env()
    
    # Setup signal handling
    def signal_handler(sig, frame):
        print("\nShutting down consumer...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 80)
    print("News Article Consumer")
    print("=" * 80)
    print(f"Broker: {config.broker.broker_type.value}")
    print(f"Topic/Subject: {config.broker.topic if config.broker.broker_type == BrokerType.KAFKA else config.broker.subject}")
    print(f"Bootstrap servers: {config.broker.bootstrap_servers}")
    print("=" * 80)
    
    try:
        # Create consumer
        consumer = ConsumerFactory.create_consumer(config)
        consumer.set_message_callback(simple_message_printer)
        
        # Start consumer (this will block)
        print("Starting consumer. Press Ctrl+C to stop.")
        consumer.start()
        
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install required dependencies:")
        print("  pip install confluent-kafka  # for Kafka")
        print("  pip install nats-py          # for NATS")
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()