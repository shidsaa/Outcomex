# System Logging

This logging journey provides professional-grade log management for the SmartSensor system, enabling effective debugging, monitoring, and analysis.
Logging key features are:
- **Structured JSON logging** for easy parsing
- **Standardized format** across all services
- **Multiple log levels** (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Contextual information** (timestamp, level, module name, message)


```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Promtail   │───▶│    Loki     │───▶│   Grafana   │───▶│     N8N     │
│ (Log Agent) │    │ (Log Store) │    │ (Dashboard) │    │ (Alerts)    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Docker Logs │    │ Time Series │    │ Visualize   │    │ Send Alerts │
│ System Logs │    │ JSON Format │    │ Metrics     │    │ Slack/Email │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## **Key Features of This Architecture**

### **Centralized Logging**
- All logs in one place (Loki)
- No need to check individual containers
- Unified search across all services

### **Advanced Search**
- Full-text search in log content
- Filter by service, level, time
- Complex queries with LogQL

### **Real-time Monitoring**
- Live log streaming in Grafana
- Instant visibility into system state
- Immediate alerting capabilities

### **Log Retention**
- Logs persist even if containers restart
- Historical analysis possible
- Time-based queries and trends

### **Correlation**
- Link logs with metrics (Prometheus)
- Correlate errors with performance
- End-to-end request tracing

### **Production Ready**
- Scalable architecture
- Industry-standard tools
- Professional monitoring capabilities

--- 
**Services & Ports**

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Prometheus** | 9090 | http://localhost:9090 | Metrics collection |
| **Loki** | 3100 | http://localhost:3100 | Log aggregation |
| **Promtail** | 9080 | - | Log collection agent |
| **Grafana** | 3001 | http://localhost:3001 | Monitoring dashboard |
| **N8N** | 5678 | http://localhost:5678 | Workflow automation |
---
## Logging Journey

Logs are created throughout the SmartSensor application using Python's `logging` module:

```python
# In consumer/consumer.py
logger.info("SmartSensor Consumer initialized")
logger.error(f"PROCESSING: Unexpected error: {e}")
logger.warning(f"HIGH SEVERITY ANOMALIES for {cleaned['device_id']}")
logger.debug(f"INGEST: Processing message {self.messages_processed}")
```

When `logger.info("SmartSensor Consumer initialized")` is called, it produces an object like:


```json
{
  "asctime": "2025-07-28 05:08:31,816",
  "levelname": "INFO",
  "name": "__main__",
  "message": "⚡ Actions taken: [{'timestamp': '2025-07-28T05:08:31.549368', 'action': 'log', 'anomaly': {'type': 'threshold', 'severity': 'high', 'reason': 'vibration reading 1.008 exceeds critical threshold 0.4', 'threshold': 0.4, 'detector': 'consumer_basic'}, 'device_id': 'sensor-2', 'sensor_data': {'pm2_5': 6.558, 'pm10': 33.216, 'dBA': 75.479, 'vibration': 1.008}}]"
}
```

**Benefits of this JSON Format are:**
- **Machine-readable** for automated processing
- **Structured data** with clear fields
- **Easy parsing** by log collection tools
- **Searchable** by specific fields


On the other hand, Docker automatically captures all stdout/stderr from containers and stores them in its log system:
`/var/lib/docker/containers/[container-id]/[container-id]-json.log`

Docker also adds metadata to each log entry:
```json
{
  "log": "{\"asctime\": \"2025-07-28 05:08:31,556\", \"levelname\": \"INFO\", \"name\": \"__main__\", \"message\": \"SmartSensor Consumer initialized\"}",
  "stream": "stdout",
  "time": "2025-07-28T05:08:31.556123456Z"
}
```

Promtail which is configured in `monitoring/promtail.yml` Watches Docker log files for changes, parses JSON logs and extracts fields, labels logs with metadata (job="docker", level="INFO"), sends logs to Loki with proper formatting and handles timestamps and log ordering. So the journey would be:


```
Docker Log File → Promtail → Parse JSON → Extract Fields → Add Labels → Send to Loki
```

Then Loki as the log aggregation system which is designed for Grafana, stores logs in time-series format. It would be optimized for log queries and searches and supports LogQL query language.

Loki stores logs with:
- **Timestamp** for time-based queries
- **Labels** for filtering (job="docker", level="INFO")
- **Log content** in compressed format
- **Index** for fast searching

Finally, Grafana connects to Loki as a data source:

```yaml
# monitoring/grafana/provisioning/datasources/datasources.yml
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
```



















### **Loki Query Language (LogQL)**

```bash
# Basic queries
{job="docker"}                    # All Docker logs
{job="docker"} |= "ERROR"         # Error logs only
{job="docker"} |= "anomaly"       # Anomaly logs

# Time-based queries
{job="docker"}[5m]                # Last 5 minutes
{job="docker"}[1h]                # Last hour

# Complex queries
{job="docker"} |= "consumer" |= "ERROR"  # Consumer error logs
{job="docker"} |= "HIGH SEVERITY"        # High severity logs


# Consumer service logs
{job="docker"} |= "Actions taken"

# Error logs from any service
{job="docker"} |= "ERROR"

# Anomaly detection logs
{job="docker"} |= "anomaly"

# High severity issues
{job="docker"} |= "HIGH SEVERITY"

# Recent logs (last 10 minutes)
{job="docker"}[10m]
```










## **Configuration Files**

### **Prometheus** (`./prometheus.yml`)
- Scrapes metrics from consumer, ML service, and RabbitMQ
- 15-second intervals

### **Promtail** (`./promtail.yml`)
- Collects Docker container logs
- Extracts container IDs and log levels
- Sends to Loki

### **Grafana** (`./grafana/`)
- Data sources: Prometheus, Loki
- Dashboard: SmartSensor Monitoring
- Auto-provisioning enabled



## **Complete Logging Flow Example**

**1.  Application Log Creation:**
```python
# In consumer/consumer.py
logger.warning(f"⚠️ HIGH SEVERITY ANOMALIES for {device_id}: {len(high_anomalies)} high-severity issues")
```

**2.  JSON Output:**
```json
{
  "asctime": "2025-07-28 05:08:31,816",
  "levelname": "WARNING",
  "name": "__main__",
  "message": "⚠️ HIGH SEVERITY ANOMALIES for sensor-2: 1 high-severity issues"
}
```

**3.  Docker Capture:**
```json
{
  "log": "{\"asctime\": \"2025-07-28 05:08:31,816\", \"levelname\": \"WARNING\", \"name\": \"__main__\", \"message\": \"⚠️ HIGH SEVERITY ANOMALIES for sensor-2: 1 high-severity issues\"}",
  "stream": "stdout",
  "time": "2025-07-28T05:08:31.816123456Z"
}
```

**4.  Promtail Processing:**
- Reads Docker log file
- Parses JSON structure
- Extracts level="WARNING"
- Adds labels: job="docker", level="WARNING"
- Sends to Loki

**5.  Loki Storage:**
- Stores with timestamp
- Indexes by labels
- Compresses for efficiency
- Ready for queries

**6.  Grafana Query:**
```bash
# In Grafana Explore:
{job="docker"} |= "HIGH SEVERITY"
```
**Result:** Shows the anomaly log in real-time dashboard


## **Troubleshooting**

### **No Logs in Grafana?**x
1. Check if Loki is ready: `curl http://localhost:3100/ready`
2. Check Promtail logs: `docker-compose logs promtail`
3. Verify log collection: `curl http://localhost:3100/loki/api/v1/labels`

### **Wrong Query Results?**
1. Use correct LogQL syntax: `{job="docker"}`
2. Check available labels: `curl http://localhost:3100/loki/api/v1/labels`
3. Test queries directly: `curl -G "http://localhost:3100/loki/api/v1/query_range"`

### **Performance Issues?**
1. Check Loki metrics: `http://localhost:3100/metrics`
2. Monitor Promtail performance
3. Adjust log retention settings

