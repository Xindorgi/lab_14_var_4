import os
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class BrokerType(Enum):
    KAFKA = "kafka"
    NATS = "nats"

@dataclass
class BrokerConfig:
    """Message broker configuration"""
    enabled: bool = False
    broker_type: BrokerType = BrokerType.KAFKA
    bootstrap_servers: List[str] = None  # For Kafka
    topic: str = "news-articles"
    group_id: str = "news-analyzer"
    nats_url: str = "nats://localhost:4222"  # For NATS
    subject: str = "news.articles"
    
    def __post_init__(self):
        if self.bootstrap_servers is None:
            self.bootstrap_servers = ["localhost:9093"]

@dataclass
class DatabaseConfig:
    """Database configuration"""
    enabled: bool = False
    db_type: str = "postgresql"  # postgresql, sqlite, mysql
    host: str = "localhost"
    port: int = 5432
    database: str = "newsdb"
    username: str = "newsuser"
    password: str = "newspass"
    
    @property
    def connection_string(self) -> str:
        if self.db_type == "postgresql":
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "sqlite":
            return f"sqlite:///{self.database}.db"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

@dataclass
class RedisConfig:
    """Redis configuration"""
    enabled: bool = False
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    @property
    def connection_string(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

@dataclass
class AnalysisConfig:
    """Analysis configuration"""
    window_size_minutes: int = 5
    sliding_interval_minutes: int = 1
    max_articles_per_window: int = 1000
    enable_sentiment_analysis: bool = False
    enable_topic_modeling: bool = False
    enable_trend_detection: bool = True
    
@dataclass
class ArrowFlightConfig:
    """Apache Arrow Flight configuration"""
    enabled: bool = False
    host: str = "localhost"
    port: int = 8815
    endpoint: str = "/arrow.flight.protocol.FlightService/"

@dataclass
class ApiConfig:
    """REST API configuration"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 8000
    cors_origins: List[str] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "analyzer.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class AppConfig:
    """Main application configuration"""
    broker: BrokerConfig
    database: DatabaseConfig
    redis: RedisConfig
    analysis: AnalysisConfig
    arrow_flight: ArrowFlightConfig
    api: ApiConfig
    logging: LoggingConfig
    
    @classmethod
    def default(cls):
        return cls(
            broker=BrokerConfig(enabled=True),
            database=DatabaseConfig(),
            redis=RedisConfig(),
            analysis=AnalysisConfig(),
            arrow_flight=ArrowFlightConfig(),
            api=ApiConfig(),
            logging=LoggingConfig()
        )

# Default configuration
DEFAULT_CONFIG = AppConfig.default()

# Environment variable overrides
def load_config_from_env() -> AppConfig:
    """Load configuration from environment variables"""
    config = AppConfig.default()
    
    # Broker configuration
    config.broker.enabled = os.getenv("BROKER_ENABLED", "true").lower() == "true"
    config.broker.broker_type = BrokerType(os.getenv("BROKER_TYPE", "kafka"))
    config.broker.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093").split(",")
    config.broker.topic = os.getenv("KAFKA_TOPIC", "news-articles")
    config.broker.group_id = os.getenv("KAFKA_GROUP_ID", "news-analyzer")
    config.broker.nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    config.broker.subject = os.getenv("NATS_SUBJECT", "news.articles")
    
    # Database configuration
    config.database.enabled = os.getenv("DATABASE_ENABLED", "false").lower() == "true"
    config.database.db_type = os.getenv("DATABASE_TYPE", "postgresql")
    config.database.host = os.getenv("DATABASE_HOST", "localhost")
    config.database.port = int(os.getenv("DATABASE_PORT", "5432"))
    config.database.database = os.getenv("DATABASE_NAME", "newsdb")
    config.database.username = os.getenv("DATABASE_USER", "newsuser")
    config.database.password = os.getenv("DATABASE_PASSWORD", "newspass")
    
    # Redis configuration
    config.redis.enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
    config.redis.host = os.getenv("REDIS_HOST", "localhost")
    config.redis.port = int(os.getenv("REDIS_PORT", "6379"))
    config.redis.db = int(os.getenv("REDIS_DB", "0"))
    config.redis.password = os.getenv("REDIS_PASSWORD")
    
    # Analysis configuration
    config.analysis.window_size_minutes = int(os.getenv("WINDOW_SIZE_MINUTES", "5"))
    config.analysis.sliding_interval_minutes = int(os.getenv("SLIDING_INTERVAL_MINUTES", "1"))
    config.analysis.max_articles_per_window = int(os.getenv("MAX_ARTICLES_PER_WINDOW", "1000"))
    config.analysis.enable_sentiment_analysis = os.getenv("ENABLE_SENTIMENT_ANALYSIS", "false").lower() == "true"
    config.analysis.enable_topic_modeling = os.getenv("ENABLE_TOPIC_MODELING", "false").lower() == "true"
    config.analysis.enable_trend_detection = os.getenv("ENABLE_TREND_DETECTION", "true").lower() == "true"
    
    # Arrow Flight configuration
    config.arrow_flight.enabled = os.getenv("ARROW_FLIGHT_ENABLED", "false").lower() == "true"
    config.arrow_flight.host = os.getenv("ARROW_FLIGHT_HOST", "localhost")
    config.arrow_flight.port = int(os.getenv("ARROW_FLIGHT_PORT", "8815"))
    
    # API configuration
    config.api.enabled = os.getenv("API_ENABLED", "true").lower() == "true"
    config.api.host = os.getenv("API_HOST", "localhost")
    config.api.port = int(os.getenv("API_PORT", "8000"))
    config.api.cors_origins = os.getenv("API_CORS_ORIGINS", "*").split(",")
    
    # Logging configuration
    config.logging.level = os.getenv("LOG_LEVEL", "INFO")
    config.logging.file = os.getenv("LOG_FILE", "analyzer.log")
    
    return config