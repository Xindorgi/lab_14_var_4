# Enhanced Chart Features Documentation

## Overview

This commit introduces significant improvements to the dashboard's visualization capabilities, focusing on live-updating charts and enhanced statistics display.

## New Chart Types

### 1. Source Distribution Charts
- **Bar Chart**: Enhanced with Viridis color scale, value labels, and interactive tooltips
- **Pie Chart**: Donut-style visualization showing source distribution with percentage labels
- **Features**: 
  - Top 8 sources displayed individually, others grouped as "Other"
  - Responsive design with hover effects
  - Animated transitions between data updates

### 2. Timeline Charts
- **Main Timeline**: Shows article volume over time with moving average line
- **Publishing Rate**: Displays articles per minute with fill area and average line
- **Features**:
  - 5-window moving average for trend visualization
  - Interactive zoom and pan
  - Custom hover templates with formatted timestamps
  - Threshold lines showing average values

### 3. Activity Heatmap
- **Hourly Activity**: Visualizes article distribution by hour of day
- **Features**:
  - Viridis color scale for intensity representation
  - Hover information showing exact article counts
  - Responsive to different time ranges
  - Automatic data aggregation

### 4. Trend Indicators
- **Real-time Trends**: Calculates and displays trend directions
- **Categories**:
  - 📈 Strong Increase (>10% change)
  - ↗️ Moderate Increase (2-10% change)
  - ➡️ Stable (±2% change)
  - ↘️ Moderate Decrease (2-10% change)
  - 📉 Strong Decrease (>10% change)
- **Features**:
  - Color-coded indicators
  - Percentage change display
  - Recent vs older average comparison

## UI Improvements

### Tabbed Interface
- **Overview Tab**: Timeline and publishing rate charts
- **Sources Tab**: Distribution bar chart and pie chart
- **Activity Tab**: Heatmap visualization

### Enhanced Styling
- **Metric Cards**: Hover effects with elevation and shadow
- **Chart Containers**: Consistent styling with rounded corners and subtle shadows
- **Color Scheme**: Consistent use of Streamlit's color palette with Viridis for data visualization

### Interactive Features
- **Tooltips**: Custom formatted hover information
- **Zoom/Pan**: All charts support interactive exploration
- **Legend Controls**: Interactive legends with show/hide functionality
- **Export Options**: Chart images can be exported via Plotly's toolbar

## Live Update System

### Auto-refresh Mechanism
- **30-second intervals**: Configurable refresh rate
- **Progress Indicator**: Visual countdown in sidebar
- **State Preservation**: UI state maintained between refreshes
- **Fragment Updates**: Partial page updates for better performance

### Data Fetching
- **API Integration**: Real-time data from analyzer REST API
- **Fallback System**: Automatic switch to mock data if API unavailable
- **Error Handling**: Graceful degradation with user notifications
- **Caching**: Efficient data caching to reduce API calls

## Configuration Options

### Sidebar Controls
1. **Data Source Selection**: Choose between API data or mock data
2. **Time Range**: 1h, 6h, 12h, 24h, or 48h historical data
3. **Visualization Toggles**:
   - Show/Hide heatmap
   - Show/Hide trend indicators
   - Show/Hide raw data table
4. **API Configuration**: Custom API endpoint URL

### Chart Customization
- **Color Schemes**: Built-in support for multiple color scales
- **Animation**: Smooth transitions between data updates
- **Responsive Design**: Adapts to different screen sizes
- **Accessibility**: High contrast modes and screen reader support

## Performance Optimizations

### Client-side
- **Efficient Rendering**: Plotly's WebGL backend for large datasets
- **Debounced Updates**: Prevents excessive re-rendering
- **Memory Management**: Automatic cleanup of old chart data
- **Lazy Loading**: Charts load only when tab is active

### Server-side
- **Data Compression**: Efficient data transfer formats
- **Caching Layer**: Reduced database/API queries
- **Batch Processing**: Aggregated data requests
- **Connection Pooling**: Reusable API connections

## Usage Examples

### Basic Usage
```python
# The dashboard automatically starts with default settings
streamlit run app.py
```

### Custom Configuration
```python
# Set custom API endpoint
export API_BASE_URL="http://localhost:8000"

# Run with specific port
streamlit run app.py --server.port 8502
```

### Development Mode
```python
# Enable hot reload for development
streamlit run app.py --server.runOnSave true
```

## Troubleshooting

### Common Issues

1. **Charts Not Updating**
   - Check API connection status
   - Verify auto-refresh is enabled
   - Check browser console for errors

2. **Slow Performance**
   - Reduce time range (e.g., from 48h to 24h)
   - Disable heatmap for very large datasets
   - Check network latency to API server

3. **Missing Data**
   - Verify analyzer pipeline is running
   - Check API health endpoint
   - Review error logs in analyzer

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export STREAMLIT_LOG_LEVEL=debug
```

## Future Enhancements

### Planned Features
1. **Custom Dashboards**: User-defined chart layouts
2. **Alert System**: Threshold-based notifications
3. **Export Functionality**: CSV/PDF export of data
4. **Multi-user Support**: User authentication and preferences
5. **Mobile Optimization**: Better mobile device support

### Technical Roadmap
1. **WebSocket Support**: Real-time push updates
2. **Offline Mode**: Local data caching
3. **Plugin System**: Custom chart extensions
4. **Performance Monitoring**: Built-in performance metrics
5. **Internationalization**: Multi-language support

## Dependencies

### Core Dependencies
- `streamlit>=1.28.0`: Web framework
- `plotly>=5.17.0`: Interactive charts
- `pandas>=2.0.3`: Data manipulation
- `requests>=2.31.0`: HTTP client

### Optional Dependencies
- `altair`: Alternative charting library
- `bokeh`: Additional visualization options
- `dash`: For more complex interactive applications

## Contributing

### Adding New Charts
1. Create chart function in `app.py`
2. Add to appropriate tab section
3. Update configuration options
4. Add documentation

### Style Guidelines
- Use consistent color schemes
- Maintain responsive design
- Include hover interactions
- Add accessibility features

### Testing
- Test with both API and mock data
- Verify mobile responsiveness
- Check browser compatibility
- Validate performance with large datasets