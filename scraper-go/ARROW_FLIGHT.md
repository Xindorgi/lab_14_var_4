# Apache Arrow Flight Server for Go Scraper

## Overview

This module implements an Apache Arrow Flight server that serves aggregated news statistics from the Go scraper. The server provides high-performance data transfer using the Arrow Flight RPC protocol.

## Features

- **Flight Protocol Implementation**: Full implementation of the Flight RPC protocol
- **Aggregated Statistics**: Serves tumbling window aggregation statistics
- **Schema Management**: Provides Arrow schema information for clients
- **Health Monitoring**: Health check endpoints for monitoring
- **Window Listing**: Lists available aggregation windows
- **Memory Management**: Efficient memory allocation with Arrow's memory pool

## Architecture

```
Go Scraper → Aggregator → Arrow Flight Server → Python Analyzer/Dashboard
```

## API Endpoints

### Flight Endpoints

1. **GetFlightInfo** - Returns flight information for requested data
2. **DoGet** - Streams Arrow RecordBatches containing aggregated statistics
3. **DoAction** - Performs actions (health check, list windows)
4. **ListActions** - Lists available actions
5. **ListFlights** - Lists available flights
6. **GetSchema** - Returns schema information

### Available Actions

- `health` - Server health check
- `list_windows` - List available aggregation windows

## Data Schema

The server provides aggregated statistics with the following schema:

| Field | Type | Description |
|-------|------|-------------|
| window_start | timestamp_ns | Start time of aggregation window |
| window_end | timestamp_ns | End time of aggregation window |
| total_articles | int32 | Total articles in window |
| publishing_rate | float64 | Articles per second |
| avg_title_length | float64 | Average title length |
| avg_desc_length | float64 | Average description length |

## Configuration

```go
type ArrowFlightConfig struct {
    Enabled  bool
    Host     string  // Default: "localhost"
    Port     int     // Default: 8815
    Endpoint string  // Flight service endpoint
}
```

## Usage

### Starting the Server

The server is automatically started when the scraper is initialized with Arrow Flight enabled:

```go
config := DefaultArrowFlightConfig()
config.Enabled = true
config.Host = "localhost"
config.Port = 8815

server, err := NewArrowFlightServer(config, aggregator)
if err != nil {
    log.Fatal(err)
}

if err := server.Start(); err != nil {
    log.Fatal(err)
}
```

### Python Client Example

```python
import pyarrow as pa
import pyarrow.flight as flight

# Connect to Flight server
client = flight.FlightClient("grpc://localhost:8815")

# Get aggregated stats
ticket = flight.Ticket(json.dumps({"action": "get_aggregated_stats"}).encode())
reader = client.do_get(ticket)
table = reader.read_all()

# Convert to pandas
df = table.to_pandas()
```

## Integration with Aggregator

The server monitors the aggregator's flush channel and caches the last 100 aggregation windows. When a client requests data, the server converts the cached statistics to Arrow RecordBatches.

## Performance Considerations

1. **Memory Usage**: Uses Arrow's memory allocator for efficient memory management
2. **Caching**: Caches up to 100 aggregation windows for fast access
3. **Batch Processing**: Sends data in Arrow RecordBatches for efficient transfer
4. **Schema Serialization**: Pre-serializes schema for faster response times

## Monitoring

### Health Check

```bash
# Using gRPC client
grpcurl -plaintext localhost:8815 arrow.flight.protocol.FlightService/DoAction \
  -d '{"type": "health"}'
```

### List Windows

```bash
grpcurl -plaintext localhost:8815 arrow.flight.protocol.FlightService/DoAction \
  -d '{"type": "list_windows"}'
```

## Dependencies

- `github.com/apache/arrow/go/v14` - Apache Arrow Go bindings
- `google.golang.org/grpc` - gRPC framework

## Testing

### Manual Testing

1. Start the Go scraper with Arrow Flight enabled
2. Use a Python client to connect and fetch data:

```python
python analyzer/arrow_client.py --host localhost --port 8815 --get-stats
```

### Integration Testing

The server is tested as part of the complete pipeline:
1. Go scraper collects and aggregates data
2. Arrow Flight server makes data available
3. Python analyzer fetches data via Flight client
4. Dashboard displays the data

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure the server is running on the correct host/port
2. **No data available**: Check if the aggregator is enabled and has processed data
3. **Schema errors**: Verify client and server are using compatible Arrow versions

### Logging

The server logs important events:
- Server startup and shutdown
- Client connections
- Data caching events
- Error conditions

## Future Enhancements

1. **Authentication**: Add TLS and authentication support
2. **Compression**: Implement Arrow compression for larger datasets
3. **Streaming**: Support real-time streaming of aggregation windows
4. **Metrics**: Add Prometheus metrics for monitoring
5. **Load Balancing**: Support multiple Flight server instances