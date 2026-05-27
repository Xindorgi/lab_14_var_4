# News Analytics Dashboard

Real-time dashboard for monitoring news scraping pipeline performance with enhanced visualizations.

## Features

- **Real-time Metrics**: Live updates of scraping statistics with auto-refresh
- **Interactive Charts**: Multiple chart types with enhanced interactivity
- **Multi-source Support**: Analyzer API integration with mock data fallback
- **Responsive Design**: Works on desktop and mobile devices
- **Tabbed Interface**: Organized visualization categories
- **Trend Analysis**: Real-time trend indicators and moving averages
- **Activity Heatmaps**: Visualize patterns by time of day

## New Enhanced Features (Commit 21)

### 📈 Advanced Visualizations
- **Timeline Charts**: With moving averages and trend lines
- **Source Distribution**: Bar charts and pie/donut charts
- **Publishing Rate**: Area charts with threshold indicators
- **Activity Heatmaps**: Hourly distribution visualization
- **Trend Indicators**: Color-coded trend analysis

### 🎨 UI Improvements
- **Tabbed Interface**: Overview, Sources, and Activity tabs
- **Enhanced Metrics Cards**: Hover effects and animations
- **Chart Containers**: Consistent styling with shadows
- **Custom Tooltips**: Formatted hover information
- **Responsive Layout**: Adapts to different screen sizes

### ⚡ Live Updates
- **Auto-refresh**: Configurable 30-second intervals
- **State Preservation**: UI state maintained between updates
- **Progress Indicators**: Visual countdown in sidebar
- **Fragment Updates**: Efficient partial page updates

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

- `API_ENABLED`: Enable analyzer API integration (default: true)
- `API_HOST`: Analyzer API host (default: localhost)
- `API_PORT`: Analyzer API port (default: 8000)

### Data Sources

1. **Analyzer API**: Real-time data from Python analyzer REST API
2. **Mock Data**: Generated synthetic data for demonstration/fallback

## Dashboard Components

### Metrics Panel
- Total articles in current window
- Publishing rate (articles/minute)
- Average title length
- Number of active sources

### Chart Tabs

#### 📈 Overview Tab
- **Timeline Chart**: Article volume with moving average
- **Publishing Rate**: Articles per minute with average line

#### 📊 Sources Tab  
- **Distribution Bar Chart**: Articles by source with Viridis colors
- **Pie/Donut Chart**: Source percentage distribution

#### 🔥 Activity Tab
- **Heatmap**: Article activity by hour of day
- **Trend Indicators**: Real-time trend analysis

### Controls Panel
- Data source selection (Analyzer API/Mock Data)
- Time range selection (1h, 6h, 12h, 24h, 48h)
- Visualization toggles (heatmap, trends, raw data)
- Auto-refresh toggle and manual refresh
- API endpoint configuration

## Architecture

### Data Flow
```
Go Scraper → Kafka/NATS → Python Analyzer → REST API → Dashboard
      ↓
Arrow Flight Server (aggregated stats)
```

### Components
- **Streamlit App**: Web interface with enhanced visualizations
- **Analyzer API Client**: Fetches real-time data from analyzer
- **Configuration**: Shared with analyzer module
- **Mock Data Generator**: Fallback when API unavailable

## New Chart Features

### Interactive Elements
- **Zoom & Pan**: All charts support interactive exploration
- **Hover Tooltips**: Custom formatted information on hover
- **Legend Controls**: Interactive show/hide functionality
- **Export Options**: Chart images via Plotly toolbar

### Visual Enhancements
- **Color Schemes**: Viridis color scale for data visualization
- **Animations**: Smooth transitions between data updates
- **Threshold Lines**: Average values and trend indicators
- **Responsive Design**: Adapts to different screen sizes

## Integration with Pipeline

### Analyzer API Integration
When `API_ENABLED=true`, the dashboard connects to the analyzer's REST API to fetch real-time statistics.

### Environment Setup
```bash
export API_ENABLED=true
export API_HOST=localhost
export API_PORT=8000
streamlit run app.py
```

## Development

### Adding New Charts

1. Create chart function in `app.py`:

```python
def create_new_chart(data):
    # Process data
    # Create Plotly figure with enhanced styling
    return fig
```

2. Add to appropriate tab section:

```python
with tab_name:
    chart = create_new_chart(data)
    if chart:
        st.plotly_chart(chart, use_container_width=True, 
                       config={'displayModeBar': True})
```

### Adding New Metrics

1. Update `create_metrics_row()` function
2. Add CSS styling for metric cards
3. Update dashboard layout

### Styling Guidelines
- Use consistent color schemes from Viridis palette
- Include hover interactions and animations
- Maintain responsive design principles
- Add accessibility features (alt text, high contrast)

## Performance Optimizations

### Client-side
- **Efficient Rendering**: Plotly's WebGL backend for large datasets
- **Debounced Updates**: Prevents excessive re-rendering
- **Memory Management**: Automatic cleanup of old chart data
- **Lazy Loading**: Charts load only when tab is active

### Server-side
- **Data Compression**: Efficient data transfer formats
- **Caching Layer**: Reduced API calls with session state
- **Batch Processing**: Aggregated data requests
- **Connection Pooling**: Reusable API connections

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
See `infra/k8s/` directory for deployment manifests.

### Cloud Deployment
- **AWS**: ECS/EKS with Application Load Balancer
- **GCP**: Cloud Run or Google Kubernetes Engine
- **Azure**: AKS or Azure Container Instances

## Monitoring

### Health Checks
- Analyzer API connectivity status
- Data freshness (last update timestamp)
- Chart rendering performance metrics
- Memory usage and response times

### Logging
- Streamlit application logs to stdout/stderr
- API request/response logging
- User interaction tracking (anonymized)

### Metrics Dashboard
- Page load time and render performance
- Data fetch latency from API
- User engagement metrics
- Error rates and recovery times

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check if analyzer API server is running
   - Verify API_HOST and API_PORT settings
   - Check network connectivity and firewall rules

2. **Charts Not Updating**
   - Verify auto-refresh is enabled
   - Check API health status
   - Review browser console for JavaScript errors

3. **Slow Performance**
   - Reduce time range (e.g., 48h → 24h)
   - Disable heatmap for large datasets
   - Increase auto-refresh interval
   - Check network latency to API server

### Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
streamlit run app.py --logger.level=debug

# Test API connectivity
python -c "
import requests
resp = requests.get('http://localhost:8000/health', timeout=2)
print(f'API Health: {resp.status_code} - {resp.json()}')
"
```

## Security Considerations

### Access Control
- Implement authentication for production deployments
- Use HTTPS for all external connections
- Restrict dashboard access to authorized users only
- Implement IP whitelisting if needed

### Data Protection
- Sanitize all user inputs and API responses
- Validate data from external sources
- Implement rate limiting for API endpoints
- Use environment variables for sensitive configuration

### Network Security
- Use VPN for internal service communication
- Implement proper firewall rules
- Monitor for suspicious activity patterns
- Regular security updates and patches

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Add docstrings for public functions
- Include example usage in documentation

## License

Part of the news scraping pipeline project.