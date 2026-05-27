package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"sync"
	"time"

	"github.com/apache/arrow/go/v14/arrow"
	"github.com/apache/arrow/go/v14/arrow/array"
	"github.com/apache/arrow/go/v14/arrow/flight"
	"github.com/apache/arrow/go/v14/arrow/memory"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// ArrowFlightServer implements Apache Arrow Flight server for aggregated data
type ArrowFlightServer struct {
	config     ArrowFlightConfig
	server     flight.Server
	aggregator *Aggregator
	mu         sync.RWMutex
	statsCache []AggregatedStats
	mem        *memory.CheckedAllocator
}

// ArrowFlightConfig contains Arrow Flight server configuration
type ArrowFlightConfig struct {
	Enabled  bool
	Host     string
	Port     int
	Endpoint string // Flight service endpoint
}

// DefaultArrowFlightConfig returns default Arrow Flight configuration
func DefaultArrowFlightConfig() ArrowFlightConfig {
	return ArrowFlightConfig{
		Enabled:  false,
		Host:     "localhost",
		Port:     8815, // Default Arrow Flight port
		Endpoint: "/arrow.flight.protocol.FlightService/",
	}
}

// NewArrowFlightServer creates a new Arrow Flight server
func NewArrowFlightServer(config ArrowFlightConfig, aggregator *Aggregator) (*ArrowFlightServer, error) {
	if !config.Enabled {
		return nil, fmt.Errorf("Arrow Flight server is disabled")
	}

	// Create memory allocator
	mem := memory.NewCheckedAllocator(memory.DefaultAllocator)

	// Create Flight server
	srv := flight.NewServerWithMiddleware(nil)
	afs := &ArrowFlightServer{
		config:     config,
		aggregator: aggregator,
		mem:        mem,
		statsCache: make([]AggregatedStats, 0, 100),
	}

	// Register Flight service
	srv.RegisterFlightService(afs)

	afs.server = srv
	return afs, nil
}

// Start starts the Arrow Flight server
func (s *ArrowFlightServer) Start() error {
	addr := fmt.Sprintf("%s:%d", s.config.Host, s.config.Port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", addr, err)
	}

	log.Printf("Arrow Flight server listening on %s", addr)

	// Start server in goroutine
	go func() {
		if err := s.server.Serve(listener); err != nil {
			log.Printf("Arrow Flight server error: %v", err)
		}
	}()

	// Start aggregation monitor
	go s.monitorAggregation()

	return nil
}

// monitorAggregation monitors aggregator and caches stats for Flight queries
func (s *ArrowFlightServer) monitorAggregation() {
	if s.aggregator == nil {
		return
	}

	for stats := range s.aggregator.GetFlushChannel() {
		s.mu.Lock()
		// Keep only last 100 windows
		if len(s.statsCache) >= 100 {
			s.statsCache = s.statsCache[1:]
		}
		s.statsCache = append(s.statsCache, stats)
		s.mu.Unlock()

		log.Printf("Arrow Flight: Cached stats for window %s - %s (%d articles)",
			stats.WindowStart.Format(time.RFC3339),
			stats.WindowEnd.Format(time.RFC3339),
			stats.TotalArticles)
	}
}

// statsToRecordBatch converts AggregatedStats to Arrow RecordBatch
func (s *ArrowFlightServer) statsToRecordBatch(stats AggregatedStats) (arrow.Record, error) {
	// Create schema
	schema := arrow.NewSchema(
		[]arrow.Field{
			{Name: "window_start", Type: arrow.FixedWidthTypes.Timestamp_ns},
			{Name: "window_end", Type: arrow.FixedWidthTypes.Timestamp_ns},
			{Name: "total_articles", Type: arrow.PrimitiveTypes.Int32},
			{Name: "publishing_rate", Type: arrow.PrimitiveTypes.Float64},
			{Name: "avg_title_length", Type: arrow.PrimitiveTypes.Float64},
			{Name: "avg_desc_length", Type: arrow.PrimitiveTypes.Float64},
			{Name: "source", Type: arrow.BinaryTypes.String},
			{Name: "source_count", Type: arrow.PrimitiveTypes.Int32},
		},
		nil,
	)

	// Create builders
	b := array.NewRecordBuilder(s.mem, schema)
	defer b.Release()

	// Convert window times
	b.Field(0).(*array.TimestampBuilder).AppendTime(stats.WindowStart)
	b.Field(1).(*array.TimestampBuilder).AppendTime(stats.WindowEnd)
	b.Field(2).(*array.Int32Builder).Append(int32(stats.TotalArticles))
	b.Field(3).(*array.Float64Builder).Append(stats.PublishingRate)
	b.Field(4).(*array.Float64Builder).Append(stats.AvgTitleLength)
	b.Field(5).(*array.Float64Builder).Append(stats.AvgDescLength)

	// Add source distribution (one row per source)
	for source, count := range stats.ArticlesBySource {
		b.Field(6).(*array.StringBuilder).Append(source)
		b.Field(7).(*array.Int32Builder).Append(int32(count))
	}

	// Build record
	record := b.NewRecord()
	return record, nil
}

// statsToRecordBatchMulti converts multiple AggregatedStats to Arrow RecordBatch
func (s *ArrowFlightServer) statsToRecordBatchMulti(stats []AggregatedStats) (arrow.Record, error) {
	if len(stats) == 0 {
		// Return empty record with schema
		schema := arrow.NewSchema(
			[]arrow.Field{
				{Name: "window_start", Type: arrow.FixedWidthTypes.Timestamp_ns},
				{Name: "window_end", Type: arrow.FixedWidthTypes.Timestamp_ns},
				{Name: "total_articles", Type: arrow.PrimitiveTypes.Int32},
				{Name: "publishing_rate", Type: arrow.PrimitiveTypes.Float64},
				{Name: "avg_title_length", Type: arrow.PrimitiveTypes.Float64},
				{Name: "avg_desc_length", Type: arrow.PrimitiveTypes.Float64},
			},
			nil,
		)
		b := array.NewRecordBuilder(s.mem, schema)
		defer b.Release()
		return b.NewRecord(), nil
	}

	// Create schema
	schema := arrow.NewSchema(
		[]arrow.Field{
			{Name: "window_start", Type: arrow.FixedWidthTypes.Timestamp_ns},
			{Name: "window_end", Type: arrow.FixedWidthTypes.Timestamp_ns},
			{Name: "total_articles", Type: arrow.PrimitiveTypes.Int32},
			{Name: "publishing_rate", Type: arrow.PrimitiveTypes.Float64},
			{Name: "avg_title_length", Type: arrow.PrimitiveTypes.Float64},
			{Name: "avg_desc_length", Type: arrow.PrimitiveTypes.Float64},
		},
		nil,
	)

	// Create builders
	b := array.NewRecordBuilder(s.mem, schema)
	defer b.Release()

	// Add each stats window as a row
	for _, stat := range stats {
		b.Field(0).(*array.TimestampBuilder).AppendTime(stat.WindowStart)
		b.Field(1).(*array.TimestampBuilder).AppendTime(stat.WindowEnd)
		b.Field(2).(*array.Int32Builder).Append(int32(stat.TotalArticles))
		b.Field(3).(*array.Float64Builder).Append(stat.PublishingRate)
		b.Field(4).(*array.Float64Builder).Append(stat.AvgTitleLength)
		b.Field(5).(*array.Float64Builder).Append(stat.AvgDescLength)
	}

	// Build record
	record := b.NewRecord()
	return record, nil
}

// Stop stops the Arrow Flight server
func (s *ArrowFlightServer) Stop() {
	if s.server != nil {
		s.server.Shutdown()
		log.Println("Arrow Flight server stopped")
	}
	if s.mem != nil {
		s.mem.AssertSize(0)
	}
}

// FlightServer interface implementation

// GetFlightInfo returns FlightInfo for a request
func (s *ArrowFlightServer) GetFlightInfo(ctx context.Context, req *flight.FlightDescriptor) (*flight.FlightInfo, error) {
	// Parse ticket request
	var ticketData map[string]interface{}
	if len(req.Cmd) > 0 {
		if err := json.Unmarshal(req.Cmd, &ticketData); err != nil {
			return nil, status.Errorf(codes.InvalidArgument, "invalid ticket: %v", err)
		}
	}

	// Determine what data is being requested
	action := ""
	if val, ok := ticketData["action"]; ok {
		action = val.(string)
	}

	switch action {
	case "get_aggregated_stats", "list_windows", "get_schema":
		// Return FlightInfo for aggregated stats
		schemaBytes := s.getAggregatedStatsSchema()
		info := &flight.FlightInfo{
			Endpoint: []*flight.FlightEndpoint{
				{
					Ticket: &flight.Ticket{
						Ticket: req.Cmd,
					},
					Location: []*flight.Location{
						{
							Uri: fmt.Sprintf("grpc://%s:%d", s.config.Host, s.config.Port),
						},
					},
				},
			},
			FlightDescriptor: req,
			TotalRecords:     -1,
			TotalBytes:       -1,
			Schema:           schemaBytes,
		}
		return info, nil

	default:
		return nil, status.Errorf(codes.Unimplemented, "action %s not implemented", action)
	}
}

// DoGet returns data stream for a ticket
func (s *ArrowFlightServer) DoGet(ticket *flight.Ticket, server flight.FlightService_DoGetServer) error {
	// Parse ticket
	var ticketData map[string]interface{}
	if len(ticket.Ticket) > 0 {
		if err := json.Unmarshal(ticket.Ticket, &ticketData); err != nil {
			return status.Errorf(codes.InvalidArgument, "invalid ticket: %v", err)
		}
	}

	action := ""
	if val, ok := ticketData["action"]; ok {
		action = val.(string)
	}

	switch action {
	case "get_aggregated_stats":
		return s.doGetAggregatedStats(server)
	case "get_schema":
		return s.doGetSchema(server)
	default:
		return status.Errorf(codes.Unimplemented, "action %s not implemented", action)
	}
}

// doGetAggregatedStats streams aggregated statistics
func (s *ArrowFlightServer) doGetAggregatedStats(server flight.FlightService_DoGetServer) error {
	s.mu.RLock()
	stats := make([]AggregatedStats, len(s.statsCache))
	copy(stats, s.statsCache)
	s.mu.RUnlock()

	// Convert stats to Arrow RecordBatch
	record, err := s.statsToRecordBatchMulti(stats)
	if err != nil {
		return status.Errorf(codes.Internal, "failed to convert stats: %v", err)
	}
	defer record.Release()

	// Write to stream
	writer := flight.NewRecordWriter(server, record.Schema())
	defer writer.Close()

	return writer.Write(record)
}

// doGetSchema streams schema information
func (s *ArrowFlightServer) doGetSchema(server flight.FlightService_DoGetServer) error {
	schemaBytes := s.getAggregatedStatsSchema()
	
	// Deserialize schema
	mem := memory.NewCheckedAllocator(memory.DefaultAllocator)
	defer mem.AssertSize(0)
	
	schema, err := flight.DeserializeSchema(schemaBytes, mem)
	if err != nil {
		return status.Errorf(codes.Internal, "failed to deserialize schema: %v", err)
	}

	// Create empty record with schema
	b := array.NewRecordBuilder(mem, schema)
	defer b.Release()
	record := b.NewRecord()
	defer record.Release()

	writer := flight.NewRecordWriter(server, schema)
	defer writer.Close()

	return writer.Write(record)
}

// getAggregatedStatsSchema returns schema for aggregated stats
func (s *ArrowFlightServer) getAggregatedStatsSchema() []byte {
	schema := arrow.NewSchema(
		[]arrow.Field{
			{Name: "window_start", Type: arrow.FixedWidthTypes.Timestamp_ns},
			{Name: "window_end", Type: arrow.FixedWidthTypes.Timestamp_ns},
			{Name: "total_articles", Type: arrow.PrimitiveTypes.Int32},
			{Name: "publishing_rate", Type: arrow.PrimitiveTypes.Float64},
			{Name: "avg_title_length", Type: arrow.PrimitiveTypes.Float64},
			{Name: "avg_desc_length", Type: arrow.PrimitiveTypes.Float64},
		},
		nil,
	)

	// Serialize schema using server's allocator
	serialized, err := flight.SerializeSchema(schema, s.mem)
	if err != nil {
		log.Printf("Failed to serialize schema: %v", err)
		return []byte{}
	}

	return serialized
}

// DoAction performs an action
func (s *ArrowFlightServer) DoAction(ctx context.Context, action *flight.Action) (results <-chan flight.Result, err error) {
	resultChan := make(chan flight.Result, 1)

	switch action.Type {
	case "health":
		// Health check
		resultChan <- flight.Result{Body: []byte(`{"status": "healthy"}`)}
	case "list_windows":
		// List available windows
		s.mu.RLock()
		windows := make([]map[string]interface{}, len(s.statsCache))
		for i, stat := range s.statsCache {
			windows[i] = map[string]interface{}{
				"window_start":  stat.WindowStart.Format(time.RFC3339),
				"window_end":    stat.WindowEnd.Format(time.RFC3339),
				"article_count": stat.TotalArticles,
			}
		}
		s.mu.RUnlock()

		response, _ := json.Marshal(windows)
		resultChan <- flight.Result{Body: response}
	default:
		resultChan <- flight.Result{Body: []byte(`{"error": "action not found"}`)}
	}

	close(resultChan)
	return resultChan, nil
}

// ListActions lists available actions
func (s *ArrowFlightServer) ListActions(ctx context.Context, req *flight.Empty) ([]*flight.ActionType, error) {
	return []*flight.ActionType{
		{Type: "health", Description: "Health check"},
		{Type: "list_windows", Description: "List available aggregation windows"},
	}, nil
}

// ListFlights lists available flights
func (s *ArrowFlightServer) ListFlights(ctx context.Context, criteria *flight.Criteria) ([]*flight.FlightInfo, error) {
	// Return info for aggregated stats flight
	schemaBytes := s.getAggregatedStatsSchema()
	ticket, _ := json.Marshal(map[string]string{"action": "get_aggregated_stats"})

	info := &flight.FlightInfo{
		Endpoint: []*flight.FlightEndpoint{
			{
				Ticket: &flight.Ticket{Ticket: ticket},
				Location: []*flight.Location{
					{Uri: fmt.Sprintf("grpc://%s:%d", s.config.Host, s.config.Port)},
				},
			},
		},
		FlightDescriptor: &flight.FlightDescriptor{
			Type: flight.DescriptorCMD,
			Cmd:  ticket,
		},
		TotalRecords: -1,
		TotalBytes:   -1,
		Schema:       schemaBytes,
	}

	return []*flight.FlightInfo{info}, nil
}

// DoPut receives data stream (not implemented for this server)
func (s *ArrowFlightServer) DoPut(server flight.FlightService_DoPutServer) error {
	return status.Error(codes.Unimplemented, "DoPut not implemented")
}

// DoExchange performs bidirectional data exchange (not implemented)
func (s *ArrowFlightServer) DoExchange(server flight.FlightService_DoExchangeServer) error {
	return status.Error(codes.Unimplemented, "DoExchange not implemented")
}

// GetSchema returns schema for a flight descriptor
func (s *ArrowFlightServer) GetSchema(ctx context.Context, req *flight.FlightDescriptor) (*flight.SchemaResult, error) {
	schemaBytes := s.getAggregatedStatsSchema()
	return &flight.SchemaResult{Schema: schemaBytes}, nil
}

// Integration with main scraper
func setupArrowFlightServer(config ArrowFlightConfig, aggregator *Aggregator) (*ArrowFlightServer, error) {
	if !config.Enabled {
		return nil, nil
	}

	server, err := NewArrowFlightServer(config, aggregator)
	if err != nil {
		return nil, err
	}

	if err := server.Start(); err != nil {
		return nil, err
	}

	return server, nil
}