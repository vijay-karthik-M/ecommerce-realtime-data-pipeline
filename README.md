# E-Commerce Streaming Platform - Complete Guide for Newcomers

Welcome! This document gets you started in 5 minutes and then guides you deeper.

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker installed (`docker --version`)
- Python 3.12+ (`python3 --version`)
- 8GB+ RAM recommended

### Start Everything

```bash
# 1. Start infrastructure
cd docker && docker-compose up -d && cd ..

# 2. Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Setup database & start streaming
python3 monitoring/setup_metrics_schema.py

# 4. In separate terminal: Start generator
python3 data_generator/run_generator.py

# 5. In separate terminal: Start ingestion
python3 streaming/kafka_to_bronze.py

# 6. Open Grafana
# http://localhost:3000
# Login: admin/admin123
# See 12 panels with live data!
```

**Done!** You have a fully functional streaming pipeline running locally. 🎉

---

## 📚 Understanding the Codebase

### For Different Roles

**I'm a Data Engineer** → Read [ARCHITECTURE.md](ARCHITECTURE.md)
- Understand Bronze/Silver/Gold layers
- Learn about data quality gates
- See performance tuning recommendations

**I'm a Software Engineer** → Read [CODE_STANDARDS.md](CODE_STANDARDS.md)
- Function naming conventions
- Comment style (Google docstrings)
- Testing patterns
- Error handling

**I'm a DevOps Engineer** → Read [DEPLOYMENT.md](DEPLOYMENT.md)
- Production deployment checklist
- Docker container setup
- Scaling recommendations
- Troubleshooting guide

**I'm a Data Analyst** → See [monitoring/](monitoring/) folder
- Understand metrics schema
- Learn how to query gold layer
- Use provided SQL queries

**I just want to run it** → Continue reading this README

### File Organization

```
├── ARCHITECTURE.md              ← System design, why decisions
├── DEPLOYMENT.md               ← Operations & troubleshooting
├── CODE_STANDARDS.md           ← Naming, comments, patterns
│
├── streaming/
│   ├── kafka_to_bronze.py      ← Ingest: Read Kafka → Write Parquet
│   ├── bronze_to_silver.py     ← Clean: Parse JSON, validate
│   ├── silver_to_gold.py       ← Aggregate: Hourly metrics
│   ├── gold_layer_guard.py     ← Quality gates (prevent bad data)
│   ├── query_delta.py          ← Debug tool (inspect layers)
│   └── utils/
│       ├── spark_session.py    ← Spark config (memory, parallelism)
│       └── delta_utils.py      ← Delta Lake helpers
│
├── data_quality/
│   └── validate_data.py        ← 7 Great Expectations suites
│
├── data_generator/
│   ├── run_generator.py        ← Entry point (start here)
│   ├── kafka_producer.py       ← Send to Kafka
│   ├── generators.py           ← Event factories
│   ├── schemas.py              ← JSON event schemas
│   └── config.py               ← Kafka config
│
├── monitoring/
│   ├── setup_metrics_schema.py ← Initialize database (RUN ONCE)
│   └── export_metrics_complete.py ← Export to Grafana
│
├── analytics/
│   └── advanced_queries.py     ← SQL examples
│
└── docker/
    └── docker-compose.yml      ← Infrastructure (Kafka, Postgres, Grafana)
```

---

## 🔨 Common Tasks

### Task: View Data in Bronze Layer
```bash
python3 streaming/query_delta.py bronze
# Outputs: 225,102 events in raw form
```

### Task: Check Data Quality
```bash
python3 data_quality/validate_data.py
# Outputs: 19/19 expectations passed ✅
```

### Task: Export Metrics to Grafana
```bash
python3 monitoring/export_metrics_complete.py
# Outputs: 8 metrics recorded
# Then refresh Grafana (F5)
```

### Task: Reset Everything
```bash
rm -rf data/bronze data/silver data/gold
python3 monitoring/setup_metrics_schema.py
python3 data_generator/run_generator.py &
python3 streaming/kafka_to_bronze.py &
```

### Task: Debug Why Grafana Shows No Data
1. Did you run `setup_metrics_schema.py`? (required once)
2. Did you run `export_metrics_complete.py`? (populates data)
3. Is PostgreSQL running? `docker ps | grep postgres`
4. Query directly: `psql -U dataeng -d analytics -c "SELECT * FROM metrics.latest_metrics LIMIT 5;"`

---

## 📊 System Architecture (High-Level)

```
Kafka Topic          Bronze                Silver              Gold
(Real Events)     (Raw Data)           (Cleaned)          (Metrics)
    │                  │                    │                  │
    ├─ clickstream ───→ Parquet ───────→ Parquet ───────→ Hourly Agg
    │   5,577,862           ↓              ↓                   ↓
    │   events/sec   225,102 raw    1,851,970        619 records
    │                                clean(100%)              │
    │                                                          ↓
    └──────────────────────────────────────────────→ PostgreSQL
                                                    (Metrics Table)
                                                           │
                                                           ↓
                                                      Grafana Dashboard
                                                      (12 Panels)
```

### Each Component

| Layer | Purpose | Storage | Count |
|-------|---------|---------|-------|
| **Bronze** | Raw data preservation | Parquet | 225K events |
| **Silver** | Cleaned, conformed data | Parquet | 1.8M events |
| **Gold** | Pre-aggregated metrics | Parquet | 619 hourly records |
| **Metrics** | KPIs for visualization | PostgreSQL | 50+ metric rows |
| **Dashboard** | Real-time monitoring | Grafana | 12 panels |

---

## 🎯 Key Concepts (Explained Simply)

### Bronze Layer ← "Keep Everything"
- Stores raw events FROM Kafka exactly as received
- Never transformed (immutable copy)
- Enables replaying/reprocessing if code changes
- Like a security camera recording (record everything, trim later)

### Silver Layer ← "Make Trustworthy"
- Parses Bronze JSON into structured columns
- Validates: no nulls, valid event types, reasonable timestamps
- Deduplicates events within sessions
- Like a notebook (clean, organized notes)

### Gold Layer ← "Pre-calculated"
- Hourly aggregates (total events, revenue, users per hour)
- Ready for Grafana dashboard (no query waiting)
- Like a summary report (numbers already calculated)

### Quality Gates ← "Guard the Door"
- 7 validation suites (schema, nulls, ranges, etc.)
- If validation FAILS: Block Gold layer writes (prevent bad data)
- Like airport security (check everything before boarding)

---

## 💡 How It Works (Execution Flow)

### Minute 1: Event Generated
```python
# data_generator/run_generator.py creates:
{"event_id": "abc", "user_id": "123", "event_type": "page_view", ...}
```

### Minute 1 (seconds later): Event Lands in Kafka
```python
# Kafka broker receives it
Topic: ecommerce.clickstream.v1
```

### Minute 1 (5 seconds later): Bronze Layer Written
```python
# kafka_to_bronze.py batches 5000 events every 5 seconds
# Writes to: data/bronze/clickstream/ingestion_date=2026-04-28/
```

### Minute 1 (10 seconds later): Silver Layer Written
```python
# bronze_to_silver.py parses & validates
# Writes to: data/silver/clickstream/event_date=2026-04-28/
```

### Minute 1 (every hour): Gold Layer Updated
```python
# silver_to_gold.py aggregates last hour's events
# Computes: total_events, revenue, unique_users, etc.
# Writes to: data/gold/hourly_metrics/
```

### Minute 2: Metrics Exported
```python
# monitoring/export_metrics_complete.py reads Gold layer
# Calculates: pipeline.revenue.total, pipeline.events.total, etc.
# Writes to: PostgreSQL metrics.latest_metrics table
```

### Minute 2 (5 seconds later): Grafana Shows It
```
Dashboard Panel: "Total Events Processed"
Value: 5,577,862
Updated: Just now
```

**Total end-to-end latency**: ~15 seconds (Kafka → Grafana)

---

## 🔍 Inspection Tools

### Tool 1: Query Bronze Layer
```bash
python3 streaming/query_delta.py bronze
```
**Output**: Raw event counts, sample JSON

### Tool 2: Validate Data Quality
```bash
python3 data_quality/validate_data.py
```
**Output**: 19 validation suite results (all should pass ✅)

### Tool 3: Quick Metrics Check
```bash
psql -U dataeng -d analytics -c "SELECT COUNT(*) FROM metrics.latest_metrics;"
```
**Output**: Number of metric records in PostgreSQL

### Tool 4: Grafana Dashboard
```
http://localhost:3000
→ Dashboards → E-Commerce Pipeline
```
**Output**: 12 live panels with trending data

---

## 🆘 Troubleshooting

| Problem | Check | Fix |
|---------|-------|-----|
| "Kafka broker connection refused" | `docker ps` | `docker-compose up -d` |
| "No data in Grafana" | Run: `psql -U dataeng -d analytics -c "SELECT * FROM metrics.latest_metrics LIMIT 1;"` | Run: `python3 monitoring/export_metrics_complete.py` |
| "OutOfMemory error" | Check system RAM | Reduce `spark.driver.memory` in `spark_session.py` |
| "Data quality check failing" | Run: `python3 data_quality/validate_data.py` | Fix upstream data or adjust check params |
| "Pipeline hanging" | Check logs: `docker logs streaming_spark_1` | Restart Docker containers |

---

## 📖 Deep Dives (Pick Your Interest)

- **Spark Structured Streaming**: See [streaming/kafka_to_bronze.py](streaming/kafka_to_bronze.py)
  - Learn: How micro-batching works, exactly-once semantics, checkpointing

- **Data Quality**: See [data_quality/validate_data.py](data_quality/validate_data.py)
  - Learn: 7 validation suites, how to block bad data, alerting

- **Metrics & Visualization**: See [monitoring/export_metrics_complete.py](monitoring/export_metrics_complete.py)
  - Learn: Metric naming conventions, dimensional tagging, Grafana integration

- **Code Standards**: See [CODE_STANDARDS.md](CODE_STANDARDS.md)
  - Learn: Google-style docstrings, naming conventions, error handling patterns

- **Architecture Decisions**: See [ARCHITECTURE.md](ARCHITECTURE.md)
  - Learn: Why Bronze-Silver-Gold, why Parquet, design tradeoffs

---

## 🎓 Learning Paths

### Path 1: "I want to understand the code" (30 minutes)
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) (high-level overview)
2. Skim [streaming/kafka_to_bronze.py](streaming/kafka_to_bronze.py) (spot patterns)
3. Read function docstrings (Google-style, easy to understand)
4. Check [CODE_STANDARDS.md](CODE_STANDARDS.md) for naming conventions

### Path 2: "I want to run this in production" (1 hour)
1. Read [DEPLOYMENT.md](DEPLOYMENT.md) (operations guide)
2. Check "Production Checklist" section
3. Review [docker/docker-compose.yml](docker/docker-compose.yml)
4. Adjust spark_session.py configs for your hardware

### Path 3: "I want to add a new metric" (30 minutes)
1. Find `export_metrics_complete.py` (monitoring folder)
2. Add new `record_metric()` call in `export_gold_metrics()`
3. Choose metric name: `pipeline.*` or `business.*`
4. Test: `python3 monitoring/export_metrics_complete.py`
5. Refresh Grafana dashboard

### Path 4: "I want to add a new quality check" (45 minutes)
1. Open [data_quality/validate_data.py](data_quality/validate_data.py)
2. Look for "suite_X_name()" functions
3. Copy existing suite, modify for your check
4. Add to suites list and rerun validation
5. Verify it passes/fails correctly

---

## 🤝 Contributing

Found a bug? Want to improve something?

1. **Bug Report**: Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting first
2. **Code Change**: Follow [CODE_STANDARDS.md](CODE_STANDARDS.md) for style
3. **New Feature**: Add comprehensive docstring (newcomers should understand!)

---

## 📞 Quick Reference

**Start everything:**
```bash
docker-compose -f docker/docker-compose.yml up -d
python3 monitoring/setup_metrics_schema.py
python3 data_generator/run_generator.py & python3 streaming/kafka_to_bronze.py &
```

**Stop everything:**
```bash
pkill -f "python3 data_generator"
pkill -f "python3 streaming"
docker-compose -f docker/docker-compose.yml down
```

**View logs:**
```bash
docker-compose logs -f kafka
docker-compose logs -f postgres
```

**Inspect data:**
```bash
# Bronze
python3 streaming/query_delta.py bronze

# Silver
python3 streaming/query_delta.py silver

# Gold
python3 streaming/query_delta.py gold

# Metrics (PostgreSQL)
psql -U dataeng -d analytics -c "SELECT * FROM metrics.latest_metrics ORDER BY recorded_at DESC LIMIT 10;"
```

---

## ✅ Success Criteria

You've successfully set up the system when:

- [ ] Docker containers running (`docker ps` shows 5+ containers)
- [ ] Grafana accessible at http://localhost:3000
- [ ] All 12 dashboard panels show data (not "No data")
- [ ] Data quality check passes (19/19 expectations)
- [ ] You can run `query_delta.py` and see Bronze/Silver/Gold stats

**If all ✅**: You're done! System is fully operational. 🎉

---

## 📚 Documentation Map

```
Start Here
    ↓
README.md (this file) ← You are here
    ├── Quick questions? → Use this file
    ├── Understand system? → ARCHITECTURE.md
    ├── Deploy to prod? → DEPLOYMENT.md
    ├── Code review? → CODE_STANDARDS.md
    └── Fix a bug? → Search [ARCHITECTURE.md](ARCHITECTURE.md) for that component
```

---

**Last Updated**: April 28, 2026  
**Version**: 1.0 - Production Ready  
**Status**: ✅ All systems operational
│   └── analytics_queries.sql
├── docs/                        # Documentation
│   ├── architecture.md
│   └── setup_guide.md
└── README.md
```

## 🚀 Quick Start (After Day 1)
```bash
# Start all services
cd docker
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f kafka
```

## 📊 Week 1 Progress
- [x] Day 1: Docker environment + Kafka setup
- [ ] Day 2-3: Data generator implementation
- [ ] Day 4-5: First Kafka pipeline
- [ ] Day 6-7: Spark streaming basics

## 📝 Learning Notes
Keep your learning notes in `docs/learning_notes.md` as you progress.

## 🎓 Key Concepts Covered
1. Docker containerization
2. Kafka message streaming
3. Spark structured streaming
4. Delta Lake medallion architecture
5. Airflow orchestration
6. Data quality frameworks
7. Observability and monitoring

## 👤 Author
Data Engineering Portfolio Project

## 📅 Start Date
Day 1 - Foundation Setup
