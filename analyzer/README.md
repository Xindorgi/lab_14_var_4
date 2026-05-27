# News Analyzer

Python-based analyzer for processing news articles from message brokers (Kafka/NATS).

## Features

- **Multi-broker support**: Kafka and NATS consumers
- **Real-time processing**: Stream processing of news articles
- **Sliding window analysis**: 5-minute sliding window processing
- **Database integration**: PostgreSQL and Redis support
- **Extensible architecture**: Plugin-based analysis modules

## Installation

### Dependencies

```bash
pip install -r requirements.txt
```

### Optional Dependencies

For specific features:

```bash
# For Kafka support
pip install confluent-kafka

# For NATS support  
pip install nats-py

# For database support
pip install psycopg2-binary redis

# For advanced analysis
pip install scikit-learn scipy
```

## Configuration

Configuration is managed through `config.py` with environment variable support.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BROKER_ENABLED` | Enable message broker | `true` |
| `BROKER_TYPE` | Broker type (`kafka` or `nats`) | `kafka` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka bootstrap servers | `localhost:9093` |
| `KAFKA_TOPIC` | Kafka topic name | `news-articles` |
| `KAFKA_GROUP_ID` | Kafka consumer group ID | `news-analyzer` |
| `NATS_URL` | NATS server URL | `nats://localhost:4222` |
| `NATS_SUBJECT` | NATS subject | `news.articles` |
| `DATABASE_ENABLED` | Enable database storage | `false` |
| `DATABASE_TYPE` | Database type (`postgresql`, `sqlite`) | `postgresql` |
| `DATABASE_HOST` | Database host | `localhost` |
| `DATABASE_PORT` | Database port | `5432` |
| `DATABASE_NAME` | Database name | `newsdb` |
| `DATABASE_USER` | Database user | `newsuser` |
| `DATABASE_PASSWORD` | Database password | `newspass` |
| `REDIS_ENABLED` | Enable Redis caching | `false` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database number | `0` |
| `WINDOW_SIZE_MINUTES` | Sliding window size | `5` |
| `SLIDING_INTERVAL_MINUTES` | Sliding interval | `1` |
| `MAX_ARTICLES_PER_WINDOW` | Maximum articles per window | `1000` |
| `ENABLE_SENTIMENT_ANALYSIS` | Enable sentiment analysis | `false` |
| `ENABLE_TOPIC_MODELING` | Enable topic modeling | `false` |
| `ENABLE_TREND_DETECTION` | Enable trend detection | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `analyzer.log` |

## Usage

### Basic Consumer

```bash
python consumer.py
```

This starts a consumer that prints incoming articles to the console.

### With Custom Processing

Create a custom callback function:

```python
from analyzer.consumer import ConsumerFactory, load_config_from_env

def my_processor(message):
    # Custom processing logic
    print(f"Processing: {message['title']}")

config = load_config_from_env()
consumer = ConsumerFactory.create_consumer(config)
consumer.set_message_callback(my_processor)
consumer.start()
```

### Sliding Window Processor

```bash
python sliding_window.py
```

Processes articles in 5-minute sliding windows with 1-minute intervals.

## Architecture

### Components

1. **Message Consumer**: Reads articles from Kafka/NATS
2. **Window Manager**: Manages sliding time windows
3. **Analysis Engine**: Processes articles within windows
4. **Storage Manager**: Stores results in database/Redis
5. **Output Handler**: Sends results to downstream systems

### Data Flow

```
Kafka/NATS → Consumer → Window Manager → Analysis Engine → Storage/Output
```

## Analysis Modules

### Available Modules

1. **Basic Statistics**
   - Article count per source
   - Publishing frequency
   - Word count distribution

2. **Trend Detection** (requires scikit-learn)
   - Emerging topics
   - Sentiment trends
   - Source popularity

3. **Topic Modeling** (requires scikit-learn)
   - LDA topic extraction
   - Topic evolution over time

4. **Sentiment Analysis** (requires NLTK/VADER)
   - Article sentiment scoring
   - Source sentiment comparison

### Adding Custom Modules

Create a new module in `analyzer/modules/`:

```python
from abc import ABC, abstractmethod

class AnalysisModule(ABC):
    @abstractmethod
    def process(self, articles: List[Dict]) -> Dict:
        pass

class MyModule(AnalysisModule):
    def process(self, articles):
        return {"my_metric": len(articles)}
```

## Database Schema

### Articles Table
```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255),
    source_type VARCHAR(50),
    title TEXT,
    link TEXT UNIQUE,
    description TEXT,
    published TIMESTAMP,
    scraped_at TIMESTAMP,
    authors JSONB,
    categories JSONB,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Analysis Results Table
```sql
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    analysis_type VARCHAR(100),
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Monitoring

### Logs
- Application logs: `analyzer.log` (rotating, 10MB max)
- Error logs: Separate error stream

### Metrics
- Articles processed per minute
- Window processing time
- Database operation latency
- Memory usage

### Health Checks
- Broker connectivity
- Database connectivity
- Redis connectivity
- Processing queue depth

## Deployment

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "sliding_window.py"]
```

### Kubernetes
See `k8s/` directory for deployment manifests.

## Performance Tuning

### Consumer Settings
- Adjust `max.poll.records` for Kafka
- Tune `session.timeout.ms` for consumer groups
- Configure `fetch.min.bytes` for throughput

### Window Processing
- Adjust window size based on article volume
- Tune sliding interval for real-time requirements
- Limit articles per window to prevent memory issues

### Database Optimization
- Use connection pooling
- Implement batch inserts
- Add appropriate indexes

## Troubleshooting

### Common Issues

1. **Consumer not receiving messages**
   - Check broker connectivity
   - Verify topic/subject exists
   - Check consumer group configuration

2. **High memory usage**
   - Reduce `MAX_ARTICLES_PER_WINDOW`
   - Increase sliding interval
   - Implement article filtering

3. **Database connection issues**
   - Check connection string
   - Verify database permissions
   - Monitor connection limits

### Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python consumer.py

# Check broker status
docker-compose -f ../infra/docker-compose.yml ps
```

## Development

### Testing
```bash
# Run unit tests
pytest tests/

# Run integration tests (requires broker)
pytest tests/integration/
```

### Code Style
```bash
# Format code
black analyzer/

# Check style
flake8 analyzer/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

Part of the news scraping project.