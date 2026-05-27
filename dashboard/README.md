# News Analytics Dashboard

Real-time dashboard for monitoring news scraping pipeline performance.

## Features

- **Real-time Metrics**: Live updates of scraping statistics
- **Interactive Charts**: Source distribution, timeline, publishing rates
- **Multi-source Support**: Mock data and Arrow Flight server integration
- **Responsive Design**: Works on desktop and mobile
- **Auto-refresh**: Configurable update intervals

## Installation

### Dependencies

```bash
pip install -r requirements.txt
```

### Optional Dependencies

For full functionality:

```bash
# For Arrow Flight support
pip install pyarrow

# For Kafka integration  
pip install confluent-kafka

# For database integration
pip install psycopg2-binary redis
```

## Usage

### Running the Dashboard

```bash
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`.

### Configuration

The dashboard automatically loads configuration from environment variables (via `analyzer/config.py`). Key variables:

- `ARROW_FLIGHT_ENABLED`: Enable Arrow Flight server integration
- `ARROW_FLIGHT_HOST`: Arrow Flight server host
- `ARROW_FLIGHT_PORT`: Arrow Flight server port

### Data Sources

1. **Mock Data**: Generated synthetic data for demonstration
2. **Arrow Flight Server**: Real aggregated data from Go scraper

## Dashboard Components

### Metrics Panel
- Total articles in current window
- Publishing rate (articles/minute)
- Average title length
- Number of active sources

### Charts
1. **Source Distribution**: Bar chart showing articles per source
2. **Timeline**: Line chart of article volume over time
3. **Publishing Rate**: Area chart of articles per minute

### Controls
- Data source selection (Mock/Arrow Flight)
- Time range selection (1h to 48h)
- Auto-refresh toggle
- Raw data display

## Architecture

### Data Flow
```
Go Scraper → Aggregation → Arrow Flight Server → Dashboard
                    ↓
              Kafka/NATS → Python Analyzer
```

### Components
- **Streamlit App**: Web interface and visualization
- **Arrow Client**: Fetches aggregated data from Go scraper
- **Configuration**: Shared with analyzer module
- **Mock Data**: Fallback when real data unavailable

## Development

### Adding New Charts

1. Create chart function in `app.py`:

```python
def create_new_chart(stats):
    # Process stats data
    # Create Plotly figure
    return fig
```

2. Add to dashboard layout:

```python
new_chart = create_new_chart(stats)
if new_chart:
    st.plotly_chart(new_chart, use_container_width=True)
```

### Adding New Metrics

1. Update `create_metrics_row()` function
2. Add to metrics display in main layout

### Styling

Custom CSS is embedded in the app. Modify the `<style>` section in `app.py` for visual changes.

## Integration with Pipeline

### Arrow Flight Integration
When `ARROW_FLIGHT_ENABLED=true`, the dashboard connects to the Go scraper's Arrow Flight server to fetch real aggregated statistics.

### Environment Setup
```bash
export ARROW_FLIGHT_ENABLED=true
export ARROW_FLIGHT_HOST=localhost
export ARROW_FLIGHT_PORT=8815
streamlit run app.py
```

## Deployment

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Kubernetes
See `k8s/dashboard.yaml` for deployment manifest.

### Cloud Deployment
- **AWS**: ECS/EKS with ALB
- **GCP**: Cloud Run or GKE
- **Azure**: AKS or Container Instances

## Monitoring

### Health Checks
- Arrow Flight server connectivity
- Data freshness (last update time)
- Chart rendering performance

### Logs
- Streamlit logs to stdout/stderr
- Application logs via Python logging module

### Metrics
- Page load time
- Data fetch latency
- User interactions

## Troubleshooting

### Common Issues

1. **Arrow Flight Connection Failed**
   - Check if Go scraper is running
   - Verify Arrow Flight server is enabled
   - Check firewall/network connectivity

2. **No Data Displayed**
   - Verify data source selection
   - Check if mock data is working
   - Review application logs

3. **High Memory Usage**
   - Reduce time range
   - Limit number of data points
   - Increase auto-refresh interval

### Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
streamlit run app.py

# Check Arrow Flight connectivity
python -c "from analyzer.arrow_client import create_arrow_client; client = create_arrow_client(); print(client.health_check())"
```

## Performance Optimization

### Data Loading
- Cache configuration and client objects
- Limit historical data based on time range
- Use pagination for large datasets

### Chart Rendering
- Use Plotly for GPU-accelerated rendering
- Limit data points in time series
- Enable chart caching where possible

### Memory Management
- Clear session state periodically
- Use generators for large data streams
- Monitor memory usage in production

## Security Considerations

### Access Control
- Implement authentication for production
- Use HTTPS for all connections
- Restrict dashboard access to authorized users

### Data Protection
- Sanitize all user inputs
- Validate data from external sources
- Implement rate limiting

### Network Security
- Use VPN for internal services
- Implement firewall rules
- Monitor for suspicious activity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

Part of the news scraping project.