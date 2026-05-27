# Infrastructure Configuration

Docker Compose setup for news scraping pipeline infrastructure.

## Services

### Core Messaging
- **Kafka** (port 9093): Distributed event streaming platform
- **Zookeeper** (port 2181): Coordination service for Kafka
- **NATS** (port 4222): Lightweight messaging system with JetStream
- **NATS UI** (port 8081): Monitoring interface for NATS

### Coordination & Storage
- **etcd** (port 2379): Distributed key-value store for coordination
- **PostgreSQL** (port 5432): Relational database for metadata
- **Redis** (port 6379): In-memory data structure store for caching

### Monitoring
- **Kafka UI** (port 8080): Web UI for Kafka cluster management

## Quick Start

### Start all services
```bash
docker-compose up -d
```

### Start specific services
```bash
# Start only Kafka and dependencies
docker-compose up -d zookeeper kafka

# Start only NATS
docker-compose up -d nats

# Start only etcd
docker-compose up -d etcd
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f kafka
```

## Service Details

### Kafka
- **Broker**: `localhost:9093` (external), `kafka:9092` (internal)
- **UI**: http://localhost:8080
- **Topics**: Auto-created when needed
- **Retention**: 7 days or 1GB per topic

### NATS
- **Server**: `localhost:4222` (external), `nats:4222` (internal)
- **Monitoring**: http://localhost:8222
- **JetStream**: Enabled for persistent messaging

### etcd
- **Client URL**: `http://localhost:2379`
- **Peer URL**: `http://localhost:2380`
- **Use case**: Distributed scraper coordination

### PostgreSQL
- **Database**: `newsdb`
- **User**: `newsuser`
- **Password**: `newspass`
- **Use case**: Article metadata storage

### Redis
- **Port**: `6379`
- **Use case**: Caching and session storage

## Configuration

### Environment Variables

#### Kafka
- `KAFKA_BROKER_ID`: Unique broker identifier
- `KAFKA_ADVERTISED_LISTENERS`: Network addresses for clients
- `KAFKA_AUTO_CREATE_TOPICS_ENABLE`: Allow automatic topic creation

#### NATS
- JetStream enabled by default (`-js` flag)
- Monitoring enabled on port 8222

#### etcd
- Single node cluster configuration
- Client and peer ports exposed

## Network

All services are connected to the `news-network` bridge network, allowing them to communicate using service names as hostnames.

## Health Checks

Each service includes health checks for reliable orchestration:

```bash
# Check service health
docker-compose ps

# View health status
docker inspect --format='{{json .State.Health}}' container_name
```

## Persistence

- **PostgreSQL**: Data persisted in `postgres_data` volume
- **Redis**: Data persisted in `redis_data` volume
- **Kafka**: Data persisted in container (ephemeral by default)

For production, mount persistent volumes for Kafka and etcd.

## Monitoring

### Kafka UI
- Access: http://localhost:8080
- Features: Topic management, message browsing, consumer group monitoring

### NATS Monitoring
- Access: http://localhost:8222
- Features: Server info, connection stats, JetStream monitoring

### etcd
```bash
# Check etcd health
docker-compose exec etcd etcdctl endpoint health

# List keys
docker-compose exec etcd etcdctl get --prefix ""
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 9093, 4222, 2379, etc. are available
2. **Service startup order**: Dependencies are handled by `depends_on`
3. **Memory limits**: Kafka and Zookeeper may require increased memory

### Logs
```bash
# Check Kafka logs
docker-compose logs kafka

# Check Zookeeper logs  
docker-compose logs zookeeper

# Check etcd logs
docker-compose logs etcd
```

### Restart Services
```bash
# Restart specific service
docker-compose restart kafka

# Recreate and restart
docker-compose up -d --force-recreate kafka
```

## Production Considerations

For production deployment:

1. **Multiple Kafka brokers**: Increase replication factor
2. **Persistent volumes**: Mount volumes for Kafka, Zookeeper, etcd
3. **Security**: Enable SSL/TLS and authentication
4. **Monitoring**: Integrate with Prometheus and Grafana
5. **Backup**: Regular backups of etcd and PostgreSQL data

## Cleanup

Remove all containers, volumes, and networks:

```bash
docker-compose down -v
```

## License

Infrastructure configuration is part of the news scraping project.