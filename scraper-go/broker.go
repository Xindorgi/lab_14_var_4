package main

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/IBM/sarama"
)

// BrokerType represents the type of message broker
type BrokerType string

const (
	BrokerTypeKafka BrokerType = "kafka"
	BrokerTypeNATS  BrokerType = "nats"
)

// BrokerConfig contains broker configuration
type BrokerConfig struct {
	Enabled     bool
	Type        BrokerType
	Brokers     []string // For Kafka: ["localhost:9093"]
	Topic       string
	NATSURL     string // For NATS: "nats://localhost:4222"
	Subject     string // For NATS
	Compression string // "none", "gzip", "snappy", "lz4"
}

// MessageBroker interface for different broker implementations
type MessageBroker interface {
	Connect() error
	Publish(article *Article) error
	PublishBatch(articles []Article) error
	Close() error
	HealthCheck() error
}

// KafkaBroker implements MessageBroker for Apache Kafka
type KafkaBroker struct {
	config   BrokerConfig
	producer sarama.SyncProducer
}

// NewKafkaBroker creates a new Kafka broker instance
func NewKafkaBroker(config BrokerConfig) (*KafkaBroker, error) {
	kafkaConfig := sarama.NewConfig()
	kafkaConfig.Producer.Return.Successes = true
	kafkaConfig.Producer.Return.Errors = true
	kafkaConfig.Producer.RequiredAcks = sarama.WaitForAll
	kafkaConfig.Producer.Compression = getCompressionCodec(config.Compression)
	kafkaConfig.Producer.Flush.Frequency = 500 * time.Millisecond
	kafkaConfig.Producer.Flush.MaxMessages = 100

	producer, err := sarama.NewSyncProducer(config.Brokers, kafkaConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create Kafka producer: %w", err)
	}

	return &KafkaBroker{
		config:   config,
		producer: producer,
	}, nil
}

func getCompressionCodec(compression string) sarama.CompressionCodec {
	switch compression {
	case "gzip":
		return sarama.CompressionGZIP
	case "snappy":
		return sarama.CompressionSnappy
	case "lz4":
		return sarama.CompressionLZ4
	default:
		return sarama.CompressionNone
	}
}

// Connect implements MessageBroker interface
func (k *KafkaBroker) Connect() error {
	// Already connected in NewKafkaBroker
	return nil
}

// Publish sends a single article to Kafka
func (k *KafkaBroker) Publish(article *Article) error {
	jsonData, err := json.Marshal(article)
	if err != nil {
		return fmt.Errorf("failed to marshal article: %w", err)
	}

	msg := &sarama.ProducerMessage{
		Topic: k.config.Topic,
		Key:   sarama.StringEncoder(article.Source),
		Value: sarama.ByteEncoder(jsonData),
		Headers: []sarama.RecordHeader{
			{
				Key:   []byte("source"),
				Value: []byte(article.Source),
			},
			{
				Key:   []byte("source_type"),
				Value: []byte(article.SourceType),
			},
		},
		Timestamp: time.Now(),
	}

	partition, offset, err := k.producer.SendMessage(msg)
	if err != nil {
		return fmt.Errorf("failed to send message to Kafka: %w", err)
	}

	log.Printf("Published article to Kafka: topic=%s, partition=%d, offset=%d, source=%s",
		k.config.Topic, partition, offset, article.Source)
	return nil
}

// PublishBatch sends multiple articles to Kafka
func (k *KafkaBroker) PublishBatch(articles []Article) error {
	if len(articles) == 0 {
		return nil
	}

	messages := make([]*sarama.ProducerMessage, 0, len(articles))
	for _, article := range articles {
		jsonData, err := json.Marshal(article)
		if err != nil {
			return fmt.Errorf("failed to marshal article: %w", err)
		}

		msg := &sarama.ProducerMessage{
			Topic: k.config.Topic,
			Key:   sarama.StringEncoder(article.Source),
			Value: sarama.ByteEncoder(jsonData),
			Headers: []sarama.RecordHeader{
				{
					Key:   []byte("source"),
					Value: []byte(article.Source),
				},
				{
					Key:   []byte("source_type"),
					Value: []byte(article.SourceType),
				},
			},
			Timestamp: time.Now(),
		}
		messages = append(messages, msg)
	}

	err := k.producer.SendMessages(messages)
	if err != nil {
		return fmt.Errorf("failed to send batch to Kafka: %w", err)
	}

	log.Printf("Published %d articles to Kafka: topic=%s", len(articles), k.config.Topic)
	return nil
}

// Close closes the Kafka producer
func (k *KafkaBroker) Close() error {
	if k.producer != nil {
		return k.producer.Close()
	}
	return nil
}

// HealthCheck checks Kafka connection health
func (k *KafkaBroker) HealthCheck() error {
	// Try to get metadata for the topic
	admin, err := sarama.NewClusterAdmin(k.config.Brokers, sarama.NewConfig())
	if err != nil {
		return fmt.Errorf("failed to create admin client: %w", err)
	}
	defer admin.Close()

	_, err = admin.ListTopics()
	if err != nil {
		return fmt.Errorf("failed to list topics: %w", err)
	}

	return nil
}

// NATSBroker implements MessageBroker for NATS (placeholder)
// Note: Would need nats.go library import
type NATSBroker struct {
	config BrokerConfig
	// conn *nats.Conn
}

// NewNATSBroker creates a new NATS broker instance
func NewNATSBroker(config BrokerConfig) (*NATSBroker, error) {
	// Implementation would connect to NATS server
	return &NATSBroker{
		config: config,
	}, nil
}

func (n *NATSBroker) Connect() error {
	// Connect to NATS server
	return fmt.Errorf("NATS broker not implemented yet")
}

func (n *NATSBroker) Publish(article *Article) error {
	return fmt.Errorf("NATS broker not implemented yet")
}

func (n *NATSBroker) PublishBatch(articles []Article) error {
	return fmt.Errorf("NATS broker not implemented yet")
}

func (n *NATSBroker) Close() error {
	return nil
}

func (n *NATSBroker) HealthCheck() error {
	return fmt.Errorf("NATS broker not implemented yet")
}

// BrokerFactory creates the appropriate broker based on configuration
func BrokerFactory(config BrokerConfig) (MessageBroker, error) {
	if !config.Enabled {
		return nil, fmt.Errorf("broker is not enabled")
	}

	switch config.Type {
	case BrokerTypeKafka:
		return NewKafkaBroker(config)
	case BrokerTypeNATS:
		return NewNATSBroker(config)
	default:
		return nil, fmt.Errorf("unknown broker type: %s", config.Type)
	}
}

// DefaultBrokerConfig returns default broker configuration
func DefaultBrokerConfig() BrokerConfig {
	return BrokerConfig{
		Enabled:     false,
		Type:        BrokerTypeKafka,
		Brokers:     []string{"localhost:9093"},
		Topic:       "news-articles",
		NATSURL:     "nats://localhost:4222",
		Subject:     "news.articles",
		Compression: "none",
	}
}