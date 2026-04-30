# DEPLOYMENT GUIDE - E-Commerce Streaming Platform

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- PostgreSQL 12+
- Grafana 10+

### Initial Setup (One-time)

```bash
# 1. Start infrastructure
cd docker
docker-compose up -d

# 2. Create Python environment
cd ..
uv venv
source .venv/bin/activate

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Setup metrics database
python3 monitoring/setup_metrics_schema.py

# 5. Start data generation
python3 data_generator/run_generator.py &

# 6. Start streaming pipelines
python3 streaming/kafka_to_bronze.py &
python3 streaming/bronze_to_silver.py &
python3 streaming/silver_to_gold.py &

# 7. Validate data quality
python3 data_quality/validate_data.py

# 8. Export metrics to Grafana
python3 monitoring/export_metrics_complete.py

# 9. Access Grafana at http://localhost:3000
```

## File Organization

### `/streaming/`
Pipeline scripts that transform data through layers:
- `kafka_to_bronze.py` - Consume Kafka → writes Parquet (raw data)
- `bronze_to_silver.py` - Clean raw data → enriched Parquet
- `silver_to_gold.py` - Aggregate → hourly metrics
- `gold_layer_guard.py` - Validate quality before writes
- `query_delta.py` - Query all layers for debugging

### `/monitoring/`
Metrics and observability (database initialization + exports):
- `setup_metrics_schema.py` - Creates PostgreSQL tables/views (RUN ONCE)
- `export_metrics_complete.py` - Exports Gold layer metrics to Grafana

### `/data_quality/`
Great Expectations validation:
- `validate_data.py` - 7-suite data quality framework

### `/data_generator/`
Synthetic event generation:
- `run_generator.py` - Entry point (starts producer)
- `kafka_producer.py` - Sends to Kafka
- `generators.py` - Event factories
- `schemas.py` - Event schemas

### `/analytics/`
Advanced SQL queries:
- `advanced_queries.py` - Business intelligence queries

## Common Operations

### Start Everything
```bash
# Terminal 1: Data generation
python3 data_generator/run_generator.py

# Terminal 2: Streaming Bronze
python3 streaming/kafka_to_bronze.py

# Terminal 3: Streaming Silver
python3 streaming/bronze_to_silver.py

# Terminal 4: Streaming Gold
python3 streaming/silver_to_gold.py

# Terminal 5: Monitor metrics
watch -n 5 'python3 monitoring/export_metrics_complete.py'
```

### Stop Everything
```bash
# Kill all Python processes
pkill -f "python3 streaming/"
pkill -f "python3 data_generator/"
pkill -f "python3 monitoring/"
```

### Check Data Status
```bash
# Query Bronze layer
python3 streaming/query_delta.py bronze

# Query Silver layer
python3 streaming/query_delta.py silver

# Query Gold layer
python3 streaming/query_delta.py gold

# Check data quality
python3 data_quality/validate_data.py
```

### Reset Everything
```bash
# WARNING: Deletes all data
rm -rf data/bronze data/silver data/gold

# Recreate metrics database
python3 monitoring/setup_metrics_schema.py

# Restart pipelines
python3 data_generator/run_generator.py &
python3 streaming/kafka_to_bronze.py &
```

## Troubleshooting

### "Connection refused" (Kafka/PostgreSQL)
1. Check Docker containers: `docker ps`
2. Restart: `docker-compose restart`
3. Check logs: `docker-compose logs kafka` or `docker-compose logs postgres`

### "OutOfMemory" errors
- Reduce batch size in `kafka_to_bronze.py` (maxOffsetsPerTrigger)
- Reduce worker processes (check Spark config)

### "Data quality checks failing"
1. Check freshness: Created >1 hour ago? Use backfill_mode=True
2. Check nulls: Run validate_data.py with debug output
3. Check schemas: Verify JSON matches expected fields

### Grafana dashboard shows "No Data"
1. Did you run `setup_metrics_schema.py`? (one-time setup)
2. Did you run `export_metrics_complete.py`? (populates data)
3. Refresh dashboard (F5)
4. Check PostgreSQL: `psql -U dataeng -d analytics -c "SELECT * FROM metrics.latest_metrics LIMIT 5;"`

## Environment Variables

Create `.env` file:
```
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
POSTGRES_HOST=localhost
POSTGRES_DB=analytics
POSTGRES_USER=dataeng
POSTGRES_PASSWORD=dataeng123
GRAFANA_URL=http://localhost:3000
```

## Production Checklist

- [ ] Use AWS Secrets Manager for credentials (not .env files)
- [ ] Enable Kafka SSL/TLS
- [ ] Enable PostgreSQL replication + backups
- [ ] Set retention policies on data layers
- [ ] Implement automated alerting on quality failures
- [ ] Use production-grade Spark (YARN/EMR instead of local[2])
- [ ] Replace manual data_freshness check with streaming uptime tracking
- [ ] Implement circuit breaker for failed pipelines
- [ ] Set up log aggregation (ELK stack)
- [ ] Enable Spark history server for debugging

## Performance Tuning

1. **Memory**: 8GB laptop uses `spark.driver.memory=1g, executor.memory=1g`
   - Increase for production servers
   
2. **Parallelism**: Set to `local[2]` for laptop
   - Increase to `local[*]` or YARN for production
   
3. **Batch interval**: 5 seconds in kafka_to_bronze.py
   - Increase for lower latency, decrease for better throughput
   
4. **Partition count**: 2 shuffle partitions
   - Increase for larger datasets

## Monitoring Dashboard

Access at `http://localhost:3000`:
- Login: admin / admin123
- Dashboard: "E-Commerce Pipeline"
- Key panels:
  - Total Events: Running total
  - Conversion Rate: Funnel analysis
  - Data Quality: Validation results
  - System Resources: CPU/Memory trends

## API Endpoints

- Kafka: localhost:9092
- PostgreSQL: localhost:5432 (dataeng/dataeng123)
- Grafana: http://localhost:3000 (admin/admin123)
- Spark UI: http://localhost:4040 (when running)

## Logs Location

- Spark logs: `/tmp/spark-*`
- Docker logs: `docker-compose logs -f`
- Python logs: stdout (configure logging module in code)

---

For more details on architecture and code structure, see [ARCHITECTURE.md](ARCHITECTURE.md)
