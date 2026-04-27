# AlloyDB Observability

## Cloud Monitoring Setup

### Enable Required APIs and Roles

```bash
# Enable Cloud Monitoring API
gcloud services enable monitoring.googleapis.com

# Grant viewer role to the service account
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SA_EMAIL" \
    --role="roles/monitoring.viewer"
```

Minimum required role: `roles/monitoring.viewer`

### AlloyDB Metric Namespace

All AlloyDB metrics live under `alloydb.googleapis.com/database/`. Use the Cloud Monitoring API or Metrics Explorer to query them.

```bash
# List all AlloyDB metrics
gcloud monitoring metrics-descriptors list \
    --filter="metric.type=starts_with(\"alloydb.googleapis.com/database/\")"
```

---

## Key Metrics

| Metric | Description | Alert Threshold |
|---|---|---|
| `alloydb.googleapis.com/database/postgresql/cpu/utilization` | CPU utilization (0–1.0) | > 0.80 sustained |
| `alloydb.googleapis.com/database/postgresql/memory/usage` | Memory bytes used | > 85% of available |
| `alloydb.googleapis.com/database/postgresql/disk/read_ops_count` | Disk read IOPS | Baseline + 3σ |
| `alloydb.googleapis.com/database/postgresql/disk/write_ops_count` | Disk write IOPS | Baseline + 3σ |
| `alloydb.googleapis.com/database/postgresql/network/connections` | Active connections | > 80% of max_connections |
| `alloydb.googleapis.com/database/postgresql/insights/aggregate/execution_time` | Cumulative query execution time | Trend alert |
| `alloydb.googleapis.com/database/postgresql/insights/aggregate/io_time` | Cumulative I/O wait time | > 20% of execution time |
| `alloydb.googleapis.com/database/postgresql/replication/replica_lag_seconds` | Replication lag on read pool nodes | > 30 seconds |
| `alloydb.googleapis.com/database/postgresql/vacuum/dead_tuple_count` | Dead tuples awaiting vacuum | > 1,000,000 per table |

---

## PromQL Patterns

These patterns are for use with Cloud Monitoring's Prometheus-compatible query interface or Managed Prometheus (GMP).

### CPU Utilization (averaged over 5 minutes)

```promql
avg_over_time(
  alloydb_googleapis_com:database_postgresql_cpu_utilization{
    project_id="PROJECT_ID",
    cluster_id="CLUSTER_ID"
  }[5m]
)
```

### Memory Usage Percentage

```promql
(
  alloydb_googleapis_com:database_postgresql_memory_usage
  /
  alloydb_googleapis_com:database_postgresql_memory_total_size
) * 100
```

### Active Connections vs Max Connections

```promql
alloydb_googleapis_com:database_postgresql_network_connections{
  project_id="PROJECT_ID",
  instance_id="INSTANCE_ID"
}
```

Compare this value against the configured `max_connections` (default 200 on pg18 instances).

### Replication Lag (read pool nodes)

```promql
max by (instance_id) (
  alloydb_googleapis_com:database_postgresql_replication_replica_lag_seconds{
    project_id="PROJECT_ID",
    cluster_id="CLUSTER_ID"
  }
)
```

### Query Execution Time Rate (per second)

```promql
rate(
  alloydb_googleapis_com:database_postgresql_insights_aggregate_execution_time{
    project_id="PROJECT_ID"
  }[5m]
)
```

### I/O Wait Ratio

```promql
rate(
  alloydb_googleapis_com:database_postgresql_insights_aggregate_io_time[5m]
)
/
rate(
  alloydb_googleapis_com:database_postgresql_insights_aggregate_execution_time[5m]
)
```

### Disk Read IOPS Rate

```promql
rate(
  alloydb_googleapis_com:database_postgresql_disk_read_ops_count{
    project_id="PROJECT_ID",
    instance_id="INSTANCE_ID"
  }[1m]
)
```

---

## Alert Policy Examples

### High CPU Alert (Cloud Monitoring JSON)

```json
{
  "displayName": "AlloyDB High CPU",
  "conditions": [
    {
      "displayName": "CPU utilization > 80%",
      "conditionThreshold": {
        "filter": "metric.type=\"alloydb.googleapis.com/database/postgresql/cpu/utilization\" AND resource.type=\"alloydb.googleapis.com/Instance\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0.8,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_MEAN"
          }
        ]
      }
    }
  ],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
```

### High Connection Count Alert

```bash
gcloud monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="AlloyDB High Connections" \
    --condition-display-name="Connections > 160 (80% of 200)" \
    --condition-filter='metric.type="alloydb.googleapis.com/database/postgresql/network/connections" resource.type="alloydb.googleapis.com/Instance"' \
    --condition-threshold-value=160 \
    --condition-threshold-duration=120s \
    --condition-comparison=COMPARISON_GT
```

### Replication Lag Alert

```bash
gcloud monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="AlloyDB Replication Lag" \
    --condition-display-name="Read pool lag > 30s" \
    --condition-filter='metric.type="alloydb.googleapis.com/database/postgresql/replication/replica_lag_seconds" resource.type="alloydb.googleapis.com/Instance"' \
    --condition-threshold-value=30 \
    --condition-threshold-duration=60s \
    --condition-comparison=COMPARISON_GT
```

---

## Dashboard Recommendations

### Recommended Dashboard Panels

1. **CPU utilization** — line chart, 1h window, all instances overlaid
2. **Memory usage %** — line chart, alert band at 85%
3. **Active connections** — line chart with max_connections reference line
4. **Read IOPS / Write IOPS** — stacked area chart
5. **Replication lag** — line chart per read pool node
6. **Query execution time rate** — line chart, top 5 queries by execution time
7. **Dead tuple count** — bar chart per table, alert at 1M

### Create a Dashboard via gcloud

```bash
gcloud monitoring dashboards create \
    --config-from-file=alloydb-dashboard.json
```

Use the Cloud Console Metrics Explorer to build panels interactively, then export the JSON for version control.

---

## Query Insights (Built-in)

AlloyDB Query Insights provides in-console query performance data without additional setup.

```bash
# Enable Query Insights on an instance
gcloud alloydb instances update INSTANCE_ID \
    --cluster=CLUSTER_ID \
    --region=REGION \
    --query-insights-enabled \
    --query-string-length=1024 \
    --record-application-tags \
    --record-client-address
```

Access via: **Cloud Console → AlloyDB → Cluster → Query Insights**

---

## Gemini CLI Extension

For PromQL metric lookup and observability automation:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/alloydb-observability
```

Provides PromQL metric templates, alert policy generators, and dashboard scaffolding for AlloyDB metrics.
