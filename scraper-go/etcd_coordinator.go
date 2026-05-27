package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
	"go.etcd.io/etcd/client/v3/concurrency"
)

// EtcdConfig contains etcd configuration
type EtcdConfig struct {
	Enabled      bool
	Endpoints    []string
	DialTimeout  time.Duration
	LeaseTTL     int64 // Time-to-live in seconds for worker registration
	WorkerPrefix string
	SourcePrefix string
	JobPrefix    string
}

// EtcdCoordinator manages distributed scraper coordination
type EtcdCoordinator struct {
	config   EtcdConfig
	client   *clientv3.Client
	session  *concurrency.Session
	workerID string
	leaseID  clientv3.LeaseID
	stopped  bool
}

// WorkerInfo represents worker registration information
type WorkerInfo struct {
	ID           string    `json:"id"`
	Status       string    `json:"status"`
	LastHeartbeat time.Time `json:"last_heartbeat"`
	Hostname     string    `json:"hostname"`
	Resources    []string  `json:"resources"`
	StartedAt    time.Time `json:"started_at"`
}

// SourceLock represents a locked news source
type SourceLock struct {
	SourceURL   string    `json:"source_url"`
	LockedBy    string    `json:"locked_by"`
	LockedAt    time.Time `json:"locked_at"`
	LastScraped time.Time `json:"last_scraped"`
}

// DefaultEtcdConfig returns default etcd configuration
func DefaultEtcdConfig() EtcdConfig {
	return EtcdConfig{
		Enabled:      false,
		Endpoints:    []string{"localhost:2379"},
		DialTimeout:  5 * time.Second,
		LeaseTTL:     30, // 30 seconds
		WorkerPrefix: "/scraper/workers/",
		SourcePrefix: "/scraper/sources/",
		JobPrefix:    "/scraper/jobs/",
	}
}

// NewEtcdCoordinator creates a new etcd coordinator
func NewEtcdCoordinator(config EtcdConfig) (*EtcdCoordinator, error) {
	if !config.Enabled {
		return nil, fmt.Errorf("etcd coordinator is disabled")
	}

	// Generate worker ID
	hostname, _ := os.Hostname()
	workerID := fmt.Sprintf("%s-%d", hostname, time.Now().UnixNano())

	// Create etcd client
	client, err := clientv3.New(clientv3.Config{
		Endpoints:   config.Endpoints,
		DialTimeout: config.DialTimeout,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create etcd client: %w", err)
	}

	// Create session for distributed locks
	session, err := concurrency.NewSession(client, concurrency.WithTTL(int(config.LeaseTTL)))
	if err != nil {
		client.Close()
		return nil, fmt.Errorf("failed to create etcd session: %w", err)
	}

	coordinator := &EtcdCoordinator{
		config:   config,
		client:   client,
		session:  session,
		workerID: workerID,
		stopped:  false,
	}

	// Register worker
	if err := coordinator.registerWorker(); err != nil {
		coordinator.Close()
		return nil, fmt.Errorf("failed to register worker: %w", err)
	}

	// Start heartbeat
	go coordinator.heartbeatLoop()

	log.Printf("Etcd coordinator initialized. Worker ID: %s", workerID)
	return coordinator, nil
}

// registerWorker registers the worker with etcd
func (ec *EtcdCoordinator) registerWorker() error {
	workerInfo := WorkerInfo{
		ID:            ec.workerID,
		Status:        "active",
		LastHeartbeat: time.Now(),
		Hostname:      func() string { h, _ := os.Hostname(); return h }(),
		Resources:     []string{"rss", "html"},
		StartedAt:     time.Now(),
	}

	infoJSON, err := json.Marshal(workerInfo)
	if err != nil {
		return fmt.Errorf("failed to marshal worker info: %w", err)
	}

	workerKey := ec.config.WorkerPrefix + ec.workerID + "/info"
	_, err = ec.client.Put(context.Background(), workerKey, string(infoJSON))
	if err != nil {
		return fmt.Errorf("failed to register worker in etcd: %w", err)
	}

	log.Printf("Worker registered in etcd: %s", ec.workerID)
	return nil
}

// heartbeatLoop periodically updates worker heartbeat
func (ec *EtcdCoordinator) heartbeatLoop() {
	ticker := time.NewTicker(time.Duration(ec.config.LeaseTTL/2) * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		if ec.stopped {
			return
		}

		if err := ec.updateHeartbeat(); err != nil {
			log.Printf("Failed to update heartbeat: %v", err)
		}
	}
}

// updateHeartbeat updates the worker's heartbeat timestamp
func (ec *EtcdCoordinator) updateHeartbeat() error {
	workerKey := ec.config.WorkerPrefix + ec.workerID + "/info"

	// Get current worker info
	resp, err := ec.client.Get(context.Background(), workerKey)
	if err != nil {
		return fmt.Errorf("failed to get worker info: %w", err)
	}

	if len(resp.Kvs) == 0 {
		// Worker info not found, re-register
		return ec.registerWorker()
	}

	// Update heartbeat in existing info
	var workerInfo WorkerInfo
	if err := json.Unmarshal(resp.Kvs[0].Value, &workerInfo); err != nil {
		return fmt.Errorf("failed to unmarshal worker info: %w", err)
	}

	workerInfo.LastHeartbeat = time.Now()
	infoJSON, err := json.Marshal(workerInfo)
	if err != nil {
		return fmt.Errorf("failed to marshal updated worker info: %w", err)
	}

	_, err = ec.client.Put(context.Background(), workerKey, string(infoJSON))
	return err
}

// AcquireSourceLock attempts to acquire a lock for a news source
func (ec *EtcdCoordinator) AcquireSourceLock(sourceURL string, timeout time.Duration) (bool, error) {
	if ec.stopped {
		return false, fmt.Errorf("coordinator is stopped")
	}

	sourceKey := ec.config.SourcePrefix + strings.ReplaceAll(sourceURL, "/", "_") + "/lock"
	mutex := concurrency.NewMutex(ec.session, sourceKey)

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	if err := mutex.Lock(ctx); err != nil {
		if err == context.DeadlineExceeded {
			return false, nil // Lock acquisition timeout
		}
		return false, fmt.Errorf("failed to acquire lock: %w", err)
	}

	// Update lock information
	lockInfo := SourceLock{
		SourceURL: sourceURL,
		LockedBy:  ec.workerID,
		LockedAt:  time.Now(),
	}

	infoJSON, err := json.Marshal(lockInfo)
	if err != nil {
		mutex.Unlock(context.Background())
		return false, fmt.Errorf("failed to marshal lock info: %w", err)
	}

	lockKey := ec.config.SourcePrefix + strings.ReplaceAll(sourceURL, "/", "_") + "/info"
	_, err = ec.client.Put(context.Background(), lockKey, string(infoJSON))
	if err != nil {
		mutex.Unlock(context.Background())
		return false, fmt.Errorf("failed to update lock info: %w", err)
	}

	log.Printf("Acquired lock for source: %s", sourceURL)
	return true, nil
}

// ReleaseSourceLock releases a lock for a news source
func (ec *EtcdCoordinator) ReleaseSourceLock(sourceURL string) error {
	if ec.stopped {
		return fmt.Errorf("coordinator is stopped")
	}

	sourceKey := ec.config.SourcePrefix + strings.ReplaceAll(sourceURL, "/", "_") + "/lock"
	mutex := concurrency.NewMutex(ec.session, sourceKey)

	// Update last scraped time
	lockKey := ec.config.SourcePrefix + strings.ReplaceAll(sourceURL, "/", "_") + "/info"
	resp, err := ec.client.Get(context.Background(), lockKey)
	if err == nil && len(resp.Kvs) > 0 {
		var lockInfo SourceLock
		if err := json.Unmarshal(resp.Kvs[0].Value, &lockInfo); err == nil {
			lockInfo.LastScraped = time.Now()
			infoJSON, _ := json.Marshal(lockInfo)
			ec.client.Put(context.Background(), lockKey, string(infoJSON))
		}
	}

	if err := mutex.Unlock(context.Background()); err != nil {
		return fmt.Errorf("failed to release lock: %w", err)
	}

	log.Printf("Released lock for source: %s", sourceURL)
	return nil
}

// GetAvailableSources returns a list of sources that are not currently locked
func (ec *EtcdCoordinator) GetAvailableSources() ([]string, error) {
	if ec.stopped {
		return nil, fmt.Errorf("coordinator is stopped")
	}

	resp, err := ec.client.Get(context.Background(), ec.config.SourcePrefix, clientv3.WithPrefix())
	if err != nil {
		return nil, fmt.Errorf("failed to get sources: %w", err)
	}

	var availableSources []string
	processed := make(map[string]bool)

	for _, kv := range resp.Kvs {
		key := string(kv.Key)
		if strings.HasSuffix(key, "/info") {
			sourcePath := strings.TrimSuffix(key, "/info")
			sourceURL := strings.TrimPrefix(sourcePath, ec.config.SourcePrefix)
			sourceURL = strings.ReplaceAll(sourceURL, "_", "/")

			if !processed[sourceURL] {
				var lockInfo SourceLock
				if err := json.Unmarshal(kv.Value, &lockInfo); err == nil {
					if lockInfo.LockedBy == "" || time.Since(lockInfo.LockedAt) > time.Duration(ec.config.LeaseTTL)*time.Second {
						availableSources = append(availableSources, sourceURL)
					}
				}
				processed[sourceURL] = true
			}
		}
	}

	return availableSources, nil
}

// RegisterSource registers a news source in etcd
func (ec *EtcdCoordinator) RegisterSource(sourceURL string, config map[string]interface{}) error {
	if ec.stopped {
		return fmt.Errorf("coordinator is stopped")
	}

	sourceKey := ec.config.SourcePrefix + strings.ReplaceAll(sourceURL, "/", "_") + "/config"
	configJSON, err := json.Marshal(config)
	if err != nil {
		return fmt.Errorf("failed to marshal source config: %w", err)
	}

	_, err = ec.client.Put(context.Background(), sourceKey, string(configJSON))
	return err
}

// GetActiveWorkers returns a list of active workers
func (ec *EtcdCoordinator) GetActiveWorkers() ([]WorkerInfo, error) {
	if ec.stopped {
		return nil, fmt.Errorf("coordinator is stopped")
	}

	resp, err := ec.client.Get(context.Background(), ec.config.WorkerPrefix, clientv3.WithPrefix())
	if err != nil {
		return nil, fmt.Errorf("failed to get workers: %w", err)
	}

	var workers []WorkerInfo
	for _, kv := range resp.Kvs {
		if strings.HasSuffix(string(kv.Key), "/info") {
			var worker WorkerInfo
			if err := json.Unmarshal(kv.Value, &worker); err == nil {
				// Check if worker is still active (heartbeat within 2*TTL)
				if time.Since(worker.LastHeartbeat) < time.Duration(ec.config.LeaseTTL*2)*time.Second {
					workers = append(workers, worker)
				}
			}
		}
	}

	return workers, nil
}

// Close cleans up etcd resources
func (ec *EtcdCoordinator) Close() error {
	ec.stopped = true

	if ec.session != nil {
		ec.session.Close()
	}

	if ec.client != nil {
		return ec.client.Close()
	}

	return nil
}

// IsLeader attempts to become the leader among workers
func (ec *EtcdCoordinator) IsLeader() (bool, error) {
	if ec.stopped {
		return false, fmt.Errorf("coordinator is stopped")
	}

	electionKey := "/scraper/leader"
	election := concurrency.NewElection(ec.session, electionKey)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := election.Campaign(ctx, ec.workerID); err != nil {
		if err == context.DeadlineExceeded {
			return false, nil // Not leader
		}
		return false, fmt.Errorf("failed to campaign for leadership: %w", err)
	}

	log.Printf("Worker %s elected as leader", ec.workerID)
	return true, nil
}