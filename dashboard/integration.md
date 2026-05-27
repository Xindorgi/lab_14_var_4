# Dashboard Integration

Integration between the dashboard and the news scraping pipeline components.

## Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Go Scraper    │────│  Message Broker │────│ Python Analyzer │
│  (Aggregation)  │    │   (Kafka/NATS)  │    │ (Sliding Window)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                         ┌───────▼───────┐
                         │ Arrow Flight  │
                         │    Server     │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │   Dashboard   │
                         │  (Streamlit)  │
                         └───────────────┘
```

## Integration Points

### 1. Arrow Flight Server (Primary)

The dashboard primarily integrates with the Go scraper via Apache Arrow Flight:

- **Protocol**: gRPC-based Arrow Flight
- **Port**: 8815 (default)
- **Data**: Aggregated statistics in Arrow RecordBatch format
- **Frequency**: Every aggregation window (configurable, default 60 seconds)

**Configuration:**
```python
from analyzer.arrow_client import create_arrow_client
from analyzer.config import load_config_from_env

config = load_config_from_env()
client = create_arrow_client(config)

if client.is_available():
    stats = client.get_aggregated_stats()
```

### 2. Message Broker (Secondary)

For real-time article streaming, the dashboard can connect directly to Kafka/NATS:

- **Kafka Topic**: `news-articles` (raw articles)
- **NATS Subject**: `news.articles` (raw articles)
- **Consumer Group**: `dashboard-consumer`

**Example Kafka Consumer:**
```python
from analyzer.consumer import ConsumerFactory
from analyzer.config import load_config_from_env

config = load_config_from_env()
config.broker.topic = "news-articles"
config.broker.group_id = "dashboard-consumer"

consumer = ConsumerFactory.create_consumer(config)
consumer.set_message_callback(process_article)
```

### 3. Python Analyzer Integration

The dashboard shares configuration and utilities with the Python analyzer:

- **Shared Config**: `analyzer/config.py`
- **Shared Clients**: Arrow Flight, Kafka, NATS
- **Data Processing**: Reuses analyzer's data structures

## Real-time Updates

### Auto-refresh Mechanism

The dashboard implements two refresh strategies:

1. **Polling**: Regular intervals (default 30 seconds)
2. **WebSocket**: Real-time push (future enhancement)

**Polling Implementation:**
```python
import time
import streamlit as st

if st.session_state.auto_refresh:
    time_since_update = (datetime.now() - st.session_state.last_update).seconds
    if time_since_update > 30:
        st.session_state.last_update = datetime.now()
        st.rerun()
```

### Data Freshness Indicators

- **Last Update Time**: Displayed in header
- **Data Source Status**: Mock vs Real data indicator
- **Connection Health**: Arrow Flight server health check

## Configuration Management

### Environment Variables

The dashboard uses the same configuration system as the analyzer:

```bash
# Arrow Flight
export ARROW_FLIGHT_ENABLED=true
export ARROW_FLIGHT_HOST=localhost
export ARROW_FLIGHT_PORT=8815

# Message Broker
export BROKER_ENABLED=true
export BROKER_TYPE=kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# Dashboard Specific
export DASHBOARD_REFRESH_INTERVAL=30
export DASHBOARD_TIME_RANGE=24h
```

### Configuration Loading

```python
from analyzer.config import load_config_from_env

@st.cache_resource
def get_config():
    return load_config_from_env()
```

## Data Processing Pipeline

### 1. Data Acquisition
- Arrow Flight client fetches aggregated statistics
- Optional: Direct broker connection for raw articles
- Fallback: Mock data generation

### 2. Data Transformation
- Convert Arrow RecordBatches to pandas DataFrames
- Calculate derived metrics
- Format for visualization

### 3. Visualization
- Plotly charts for interactive visualizations
- Streamlit components for UI
- Real-time updates

### 4. User Interaction
- Filtering by time range
- Data source selection
- Chart customization

## Error Handling

### Connection Failures

1. **Arrow Flight Unavailable**:
   - Fall back to mock data
   - Display warning to user
   - Continue polling for recovery

2. **Broker Connection Lost**:
   - Retry with exponential backoff
   - Cache last known good state
   - Notify user of degraded functionality

### Data Validation

- Validate schema of incoming Arrow data
- Check data freshness (timestamps)
- Sanitize user inputs for security

## Performance Considerations

### Caching Strategy

- Cache configuration objects
- Cache Arrow Flight connections
- Cache processed data with TTL

### Memory Management

- Limit historical data retention
- Clear session state periodically
- Use efficient data structures

### Network Optimization

- Batch Arrow Flight requests
- Compress data transfer
- Implement connection pooling

## Monitoring and Logging

### Dashboard Metrics

- Page load time
- Data fetch latency
- User interaction events
- Error rates

### Integration Health Checks

- Arrow Flight server connectivity
- Broker connectivity
- Data freshness
- System resource usage

### Logging

- Application logs to stdout/stderr
- Structured logging for analysis
- Audit logs for user actions

## Security Considerations

### Data Access

- Authentication for production deployment
- Authorization for sensitive operations
- Audit logging for compliance

### Network Security

- TLS for Arrow Flight connections
- SASL for Kafka authentication
- Firewall rules for service isolation

### Input Validation

- Sanitize all user inputs
- Validate data from external sources
- Implement rate limiting

## Deployment Scenarios

### Development
- Mock data only
- Local Arrow Flight server
- No authentication

### Staging
- Real data from staging pipeline
- Basic authentication
- Performance monitoring

### Production
- High-availability deployment
- Full authentication/authorization
- Comprehensive monitoring
- Automated failover

## Future Enhancements

### Planned Integrations

1. **WebSocket Support**: Real-time push updates
2. **Alerting System**: Threshold-based notifications
3. **Historical Analysis**: Long-term trend visualization
4. **Multi-tenant Support**: Separate workspaces for teams

### Technical Improvements

1. **Edge Caching**: CDN for static assets
2. **Progressive Web App**: Offline functionality
3. **Mobile Optimization**: Responsive design improvements
4. **Accessibility**: WCAG 2.1 compliance

## Troubleshooting Guide

### Common Issues

1. **No Data Displayed**
   - Check Arrow Flight server status
   - Verify configuration values
   - Review application logs

2. **High Latency**
   - Monitor network connectivity
   - Check server resource usage
   - Review query performance

3. **Connection Errors**
   - Verify firewall rules
   - Check service availability
   - Review authentication credentials

### Debugging Tools

- Dashboard debug mode
- Network traffic inspection
- Performance profiling
- Log analysis

## Support and Maintenance

### Regular Maintenance

- Update dependencies
- Security patches
- Performance optimization
- Backup configuration

### Monitoring

- Uptime monitoring
- Performance metrics
- Error tracking
- User feedback collection

### Documentation

- Keep integration docs updated
- Maintain API documentation
- Update deployment guides
- Create troubleshooting resources