# ARCHITECTURE - E-Commerce Streaming Platform

## System Overview

```
┌─────────┐      ┌──────────┐      ┌─────────┐      ┌──────────┐
│ Kafka   │──→   │ Bronze   │──→   │ Silver  │──→   │ Gold     │
│ Topics  │      │ (Raw)    │      │ (Clean) │      │ (Agg.)   │
└─────────┘      └──────────┘      └─────────┘      └──────────┘
     ▲                │                  │                │
  (Generator)         └──────┘───────────┘────────────────┘
                                                    │
                                            ┌───────▼────────┐
                                            │  PostgreSQL    │
                                            │  (Metrics)     │
                                            └────────────────┘
                                                    │
                                            ┌───────▼────────┐
                                            │  Grafana       │
                                            │  (Dashboards)  │
                                            └────────────────┘
```

## Lambda Architecture

This system implements a **Lambda Architecture** (batch + streaming):

### Real-time Path (Streaming)
- Kafka → Bronze (Raw events, immediately)
- Bronze → Silver (Cleaned events with low latency)
- Silver → Gold (Hourly aggregates via micro-batches)
- Gold → PostgreSQL (Visible in Grafana seconds after event)

### Data Quality Path
- Each layer validates quality gates
- Failures block downstream writes
- Alerts on quality degradation

## Layer Definitions

### Bronze Layer ("Data Lake - Raw Data Preservation")

**Purpose**: Immutable record of all events received

**Schema**:
- Raw Kafka value (JSON string, unparsed)
- Metadata: source topic, partition, offset, timestamp, ingestion date
- Partitioned by: ingestion_date (YYYY-MM-DD)

**Storage**: Parquet (compressed, efficient reads)

**Characteristics**:
- Write-once (no updates)
- Enable reprocessing if Silver transformation logic changes
- Full audit trail

**Example Flow**:
```
Kafka: {"event_id": "123", ...}
        ↓
Bronze: value (raw JSON) + ingestion_timestamp
        ↓ (every 5 seconds, exactly-once checkpoint recovery)
Parquet: data/bronze/clickstream/ingestion_date=2026-04-28/part-*.parquet
```

### Silver Layer ("Data Warehouse - Cleaned & Enriched")

**Purpose**: Conformed, trustworthy dataset for analytics

**Schema**:
- event_id, user_id, session_id, event_type
- product_id, price, category, device_type, country
- timestamp (parsed to datetime), processed_at

**Storage**: Parquet (partitioned by event_date)

**Transformations**:
1. Parse JSON from Bronze (validation, error handling)
2. Type casting (string → timestamp)
3. Deduplication (session_id + event_id)
4. Null checking (fail on required fields)
5. Domain validation (event_type ∈ {page_view, search, ...})

**Quality Gates**:
- No nulls in required columns
- All event_types valid
- No duplicate events (within session)
- Timestamp within expected range

**Characteristics**:
- Single source of truth for events
- Data engineers own this schema
- Evolves carefully (breaking changes coordinated)

### Gold Layer ("Data Mart - Aggregated Metrics")

**Purpose**: Pre-calculated KPIs for BI/reporting

**Schema** (Hourly Aggregates):
- hour_partition (YYYY-MM-DD HH:00:00)
- event_type (categorical)
- device_type (categorical)
- event_count (volume)
- total_value (revenue)
- unique_users (cardinality)
- avg_price (average)

**Storage**: Parquet (partitioned by hour, device_type, event_type)

**Calculations**:
- Count aggregations (SUM)
- Cardinality (HyperLogLog or approx_count_distinct)
- Average prices (AVG)
- Revenue totals (SUM)

**Quality Gates**:
- Values >= 0 (no negative metrics)
- Event count >= unique_users (logical constraint)
- Conversion rates ≤ 100%

**Characteristics**:
- Immutable (append-only)
- Optimized for Grafana queries
- No windowed aggregations (hourly only)

## Data Quality Framework

**7 Validation Suites** (Great Expectations):

1. **Schema Validation**
   - Column types correct
   - Required columns present
   - Example: user_id is STRING, not NULL

2. **Null Checks**
   - Primary keys never null
   - Event_type never null
   - Fail-fast pattern

3. **Range Constraints**
   - Prices >= 0
   - Timestamps within expected range
   - User IDs follow pattern

4. **Set Membership**
   - event_type ∈ {page_view, search, add_to_cart, checkout_started, checkout_completed}
   - device_type ∈ {mobile, desktop}
   - Enum validation

5. **Uniqueness Checks**
   - No duplicate events within session (per hour)
   - Event IDs unique globally

6. **Referential Integrity**
   - Every event_id has parent user_id
   - Every user_id has session_id
   - Session consistency

7. **Completeness & Freshness**
   - Data arrives within 1 hour of event time
   - No gaps in time series > 30 minutes
   - Backfill mode (optional, for historical data)

**Blocking Behavior**:
- Suites 1-5: CRITICAL - Block Gold writes if fail
- Suite 7: WARNING - Log but don't block (optional with backfill_mode)

## Metrics & Monitoring

### Metrics Exported to PostgreSQL

**Snapshot Metrics** (latest values):
```
pipeline.revenue.total         = $838,488,520
pipeline.events.total          = 5,577,862
pipeline.users.unique          = 5,577,862
pipeline.conversion.rate       = 100.0%
pipeline.quality.score         = 100.0%
```

**Dimensional Metrics** (sliceable):
```
pipeline.events.by_type: {page_view: 3.7M, search: 872K, ...}
pipeline.events.by_device: {mobile: 2.8M, desktop: 2.7M}
```

**Time-Series Metrics** (for graphs):
```
pipeline.events.total (recorded_at: timestamp)
business.funnel.* (each stage with drop-off)
system.cpu_usage_percent (CPU trend)
system.memory_usage_percent (Memory trend)
```

### Grafana Dashboard Panels

1. **Total Events Processed** (stat) - Count of all events
2. **Event Processing Rate** (gauge) - Events/second
3. **Overall Conversion Rate** (gauge) - Checkout completion %
4. **Active Alerts** (stat) - Failed quality checks
5. **Events Over Time** (line chart) - Hourly trend
6. **Events by Type** (pie chart) - Funnel stages distribution
7. **Conversion Funnel** (bar chart) - Drop-off analysis
8. **Pipeline Success Rate** (gauge) - Execution success %
9. **Average Pipeline Duration** (stat) - Execution time
10. **Data Quality Status** (table) - All validations
11. **Recent Pipeline Runs** (table) - Execution history
12. **System Resources** (line chart) - CPU/Memory trend

## Technology Stack

### Streaming
- **Apache Spark** (PySpark 3.4.1)
- **Structured Streaming** (micro-batch architecture)
- **Kafka** (event bus)
- **Delta Lake** (transaction log, schema enforcement)

### Data Storage
- **Parquet** (columnar format, compression)
- **PostgreSQL** (OLAP metrics, Grafana datasource)

### Data Quality
- **Great Expectations** (7 validation suites)
- **Pandas** (data manipulation, fallback synthetic data)

### Monitoring & Visualization
- **Grafana** (12-panel dashboard)
- **PostgreSQL** (metrics storage)

### Deployment
- **Docker** (containerized infrastructure)
- **Docker Compose** (orchestration)
- **Python 3.12** (runtime environment)

## Design Patterns

### 1. Bronze-Silver-Gold Medallion Architecture

**Why**:
- Bronze: Immutable audit trail enables replay/reprocessing
- Silver: Single source of truth for transformed data
- Gold: Pre-calculated metrics for BI/reporting

**Tradeoff**: Storage increases 3x (duplicate data across layers)
**Benefit**: Schema isolation, independent scaling, audit trail

### 2. Micro-batch Streaming (vs. True Streaming)

**Why**:
- Exactly-once semantics guaranteed (checkpoint recovery)
- Simpler code than event-by-event processing
- Better resource efficiency (batch processing is faster)

**Tradeoff**: Latency ~5 seconds (per batch interval)
**Benefit**: No message loss, simple fault recovery

### 3. Quality Gates (Early Validation)

**Why**:
- Prevent bad data flowing to analytics
- Fail fast at Silver/Gold boundaries
- Clear responsibility: which layer caught the error

**Tradeoff**: Delays writes if quality check fails
**Benefit**: Data trust, easier debugging

### 4. Checkpoint-based Recovery

**Why**:
- Spark tracks offset: "processed up to Kafka offset 12,345"
- On restart: Resume from offset 12,346 (no duplicates/gaps)
- Handled by framework (no manual recovery)

**Tradeoff**: State stored on disk (~100MB per stream)
**Benefit**: Zero message loss, automatic recovery

### 5. Metrics-driven Observability

**Why**:
- Export KPIs to time-series database
- Grafana visualizes trends (not spot checks)
- Alerts on anomalies automatically

**Tradeoff**: Additional schema maintenance
**Benefit**: Operational visibility, trend analysis

## Code Organization & Naming

### File Naming
- `kafka_to_bronze.py` = Source → Destination naming
- `validate_data.py` = Verb + object pattern
- `config.py` = Configuration container

### Function Naming
- `get_spark_session()` = Getter pattern (factory)
- `record_metric()` = Verb + object pattern
- `ensure_metrics_table()` = Defensive pattern (idempotent)

### Variable Naming
- `KAFKA_BOOTSTRAP_SERVERS` = Config constants (UPPERCASE)
- `df` = DataFrame (Spark/Pandas convention)
- `conn` = Database connection (abbreviated for brevity)

## Performance Considerations

### Memory Usage
- Driver: 512MB → 1GB (Py4J overhead)
- Executor: 512MB (per task)
- Total: ~2GB for local[2] Spark

### CPU Usage
- 2 worker cores (local[2] parallelism)
- Single CPU spike during aggregation (1 core maxed)
- Scaling: Add Spark workers for production

### I/O Performance
- Parquet is column-oriented (efficient filtering)
- Partitioning (by date) enables partition pruning
- Checkpoint directory on fast storage (SSD recommended)

## Failure Scenarios & Recovery

| Scenario | Behavior | Recovery |
|----------|----------|----------|
| Kafka partition fails | Stream pauses, no data loss | Restart Kafka, pipeline resumes |
| Spark driver crashes | All queries fail immediately | Restart script (checkpoint resumes from offset) |
| PostgreSQL down | Metrics export fails | Reconnect, re-run export |
| Quality gate fails | Gold writes blocked, alert | Fix upstream data, retry |
| Disk full | Checkpoint write fails | Free space, restart |

## Future Enhancements

1. **Real-time streaming** (vs. micro-batch)
   - Use Spark Structured Streaming with trigger(once=True)
   - Lower latency but more complex state management

2. **Feature store** (ML preprocessing)
   - Pre-calculate features from Gold layer
   - Enable ML pipelines

3. **Data lineage** (audit trail)
   - Track which transformations created each row
   - Debug data quality issues

4. **Incremental aggregations**
   - Update Gold layer instead of recompute
   - Faster, lower CPU (tradeoff: complex state)

5. **Multi-sink exports**
   - Export to Redshift, BigQuery, etc.
   - Not just PostgreSQL

---

## Related Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Operation guide
- [Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Delta Lake Architecture](https://docs.delta.io/latest/delta-intro.html)
- [Great Expectations Docs](https://docs.greatexpectations.io/)
