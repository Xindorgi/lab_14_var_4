# etcd Configuration

etcd is a distributed key-value store used for distributed scraper coordination.

## Service Configuration

### Docker Compose
The etcd service is configured in `docker-compose.yml`:

```yaml
etcd:
  image: quay.io/coreos/etcd:v3.5.0
  container_name: etcd
  environment:
    ETCD_ADVERTISE_CLIENT_URLS: "http://etcd:2379"
    ETCD_LISTEN_CLIENT_URLS: "http://0.0.0.0:2379"
    ETCD_LISTEN_PEER_URLS: "http://0.0.0.0:2380"
    ETCD_INITIAL_ADVERTISE_PEER_URLS: "http://etcd:2380"
    ETCD_INITIAL_CLUSTER: "etcd=http://etcd:2380"
    ETCD_INITIAL_CLUSTER_TOKEN: "etcd-cluster"
    ETCD_INITIAL_CLUSTER_STATE: "new"
  ports:
    - "2379:2379"
    - "2380:2380"
  networks:
    - news-network
```

### Ports
- **2379**: Client port (external access: `localhost:2379`)
- **2380**: Peer port (internal cluster communication)

### Network
- Service name: `etcd`
- Internal URL: `http://etcd:2379`
- External URL: `http://localhost:2379`

## Usage

### Starting etcd
```bash
docker-compose up -d etcd
```

### Checking Health
```bash
docker-compose exec etcd etcdctl endpoint health
```

### Basic Operations

#### Set a key-value pair
```bash
docker-compose exec etcd etcdctl put /scraper/config "value"
```

#### Get a value
```bash
docker-compose exec etcd etcdctl get /scraper/config
```

#### Watch for changes
```bash
docker-compose exec etcd etcdctl watch /scraper/ --
```

#### List all keys with prefix
```bash
docker-compose exec etcd etcdctl get --prefix /scraper
```

## Scraper Coordination Schema

### Key Structure
```
/scraper/
  ├── workers/
  │   ├── {worker-id}/
  │   │   ├── status: "active"|"inactive"
  │   │   ├── last_heartbeat: timestamp
  │   │   └── resources: JSON list
  ├── sources/
  │   ├── {source-url}/
  │   │   ├── locked_by: worker-id or empty
  │   │   ├── last_scraped: timestamp
  │   │   └── config: JSON
  ├── jobs/
  │   ├── {job-id}/
  │   │   ├── status: "pending"|"running"|"completed"
  │   │   └── assigned_to: worker-id
  └── config/
      ├── scraping_interval: 300
      └── max_workers: 10
```

### Worker Registration
1. Worker generates unique ID
2. Creates key: `/scraper/workers/{worker-id}/status` = "active"
3. Updates heartbeat: `/scraper/workers/{worker-id}/last_heartbeat` = current timestamp
4. Periodically updates heartbeat (every 30 seconds)

### Source Locking
1. Worker tries to acquire lock: `etcdctl lock /scraper/sources/{source-url}`
2. If successful, updates `locked_by` field
3. Performs scraping
4. Releases lock and updates `last_scraped`

### Leader Election
For master-worker pattern:
```bash
# Elect a leader
docker-compose exec etcd etcdctl elect /scraper/leader worker-id
```

## Go Client Configuration

### Dependencies
```go
import "go.etcd.io/etcd/client/v3"
```

### Connection
```go
config := clientv3.Config{
    Endpoints:   []string{"http://localhost:2379"},
    DialTimeout: 5 * time.Second,
}
```

### Example: Worker Registration
```go
func registerWorker(client *clientv3.Client, workerID string) error {
    key := fmt.Sprintf("/scraper/workers/%s/status", workerID)
    _, err := client.Put(context.Background(), key, "active")
    return err
}
```

## Monitoring

### Metrics
etcd exposes metrics on port 2379:
- `http://localhost:2379/metrics`

### Logs
```bash
docker-compose logs etcd
```

### Performance Monitoring
- Watch for increasing latency
- Monitor memory usage
- Check disk I/O for persistent storage

## Backup and Recovery

### Snapshot
```bash
docker-compose exec etcd etcdctl snapshot save snapshot.db
```

### Restore
```bash
docker-compose exec etcd etcdctl snapshot restore snapshot.db
```

## Security Considerations

### Production Deployment
1. Enable TLS/SSL encryption
2. Set up authentication
3. Use firewall rules
4. Regular backups
5. Monitor access logs

### Access Control
```bash
# Enable authentication
docker-compose exec etcd etcdctl auth enable

# Create user
docker-compose exec etcd etcdctl user add username

# Set role
docker-compose exec etcd etcdctl role add scraper-role
```

## Troubleshooting

### Common Issues

1. **Connection refused**
   - Check if etcd is running: `docker-compose ps etcd`
   - Verify port mapping: `netstat -tlnp | grep 2379`

2. **High latency**
   - Check disk performance
   - Monitor network connectivity
   - Consider increasing resources

3. **Cluster health issues**
   ```bash
   docker-compose exec etcd etcdctl endpoint status
   docker-compose exec etcd etcdctl endpoint health
   ```

### Log Analysis
```bash
# View logs
docker-compose logs etcd

# Follow logs
docker-compose logs -f etcd

# Check for errors
docker-compose logs etcd | grep -i error
```

## Scaling

### Single Node
Suitable for development and testing.

### Multi-Node Cluster
For production:
1. Deploy 3 or 5 nodes
2. Configure peer URLs
3. Set up load balancing
4. Implement monitoring

### Example 3-Node Cluster
```yaml
# etcd1
ETCD_INITIAL_CLUSTER="etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380"

# etcd2
ETCD_INITIAL_CLUSTER="etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380"

# etcd3
ETCD_INITIAL_CLUSTER="etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380"
```

## Resources

- [etcd Documentation](https://etcd.io/docs/)
- [etcd GitHub](https://github.com/etcd-io/etcd)
- [etcdctl Command Reference](https://etcd.io/docs/v3.5/dev-guide/interacting_v3/)