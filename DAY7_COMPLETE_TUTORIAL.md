# 📊 DAY 7: MONITORING & DASHBOARDS - COMPLETE TUTORIAL

**Duration:** 4-6 hours  
**Difficulty:** Intermediate  
**Prerequisites:** Days 1-3 completed (infrastructure + pipeline running)

---

# 🎯 LEARNING OBJECTIVES

By the end of this tutorial, you will:
- ✅ Understand monitoring fundamentals (metrics, time-series, dashboards)
- ✅ Create metrics schema in PostgreSQL
- ✅ Export metrics from Spark to PostgreSQL
- ✅ Configure Grafana datasource
- ✅ Build production-ready dashboards
- ✅ Set up alerts
- ✅ Implement SLOs/SLIs
- ✅ Answer interview questions confidently

---

# 📚 PART 1: THEORY (30 MINUTES)

## 🔍 What is Monitoring?

**Monitoring** = Collecting, storing, and visualizing system metrics to understand health and performance.

### **The Three Pillars of Observability**

1. **Metrics** (Numbers over time)
   - Example: CPU usage, event count, latency
   - Best for: Dashboards, alerts, trends

2. **Logs** (Text records of events)
   - Example: "ERROR: Connection timeout at 10:32:15"
   - Best for: Debugging, audit trails

3. **Traces** (Request flow through system)
   - Example: Request A → Service 1 → Service 2 → Database
   - Best for: Distributed systems, latency analysis

**Today we focus on METRICS**

---

## 📊 Types of Metrics

### **1. Counter (Always Increasing)**
```
Time  | Events Processed
10:00 | 1000
10:01 | 1050  (+50)
10:02 | 1100  (+50)
```
**Use for:** Total events, total errors, total revenue

### **2. Gauge (Can Increase or Decrease)**
```
Time  | Memory Usage (MB)
10:00 | 1024
10:01 | 1536  (+512)
10:02 | 1280  (-256)
```
**Use for:** Current memory, active connections, queue depth

### **3. Histogram (Distribution)**
```
Latency Range | Count
0-5s          | 1000
5-10s         | 300
10-15s        | 50
15-20s        | 10
```
**Use for:** Response time distribution, percentiles (p50, p95, p99)

---

## 🎨 Dashboard Design Principles

### **The 5-Second Rule**
> "Can someone understand system status in 5 seconds?"

**Good Dashboard:**
```
🟢 Pipeline: Healthy
📊 Events: 16,783 (↑ 2.3%)
⏱️ Latency: 8.5s (p95)
```

**Bad Dashboard:**
```
Table with 50 rows of raw data
Tiny text, no colors
Requires scrolling
```

### **Color Psychology**
- 🟢 Green = Good, healthy, normal
- 🟡 Yellow = Warning, degraded
- 🔴 Red = Critical, failed, action needed
- 🔵 Blue = Informational

---

## 🚨 The 4 Golden Signals (Google SRE)

**For ANY system, monitor these 4:**

1. **Latency** - How long?
   - Example: 8.5 seconds (p95) to process event

2. **Traffic** - How much?
   - Example: 50 events/second

3. **Errors** - What's failing?
   - Example: 0.2% error rate

4. **Saturation** - How full?
   - Example: Memory at 85%

**Apply to our pipeline:**
```
Latency:    Kafka → Bronze → Silver latency
Traffic:    Events/second ingested
Errors:     Failed Spark tasks
Saturation: Executor memory usage
```

---

## 📐 SLA vs SLO vs SLI

### **SLI (Service Level Indicator)**
- **What:** Quantitative metric
- **Example:** "95% of events processed in <10 seconds"

### **SLO (Service Level Objective)**
- **What:** Target for SLI
- **Example:** "99.9% availability per month"

### **SLA (Service Level Agreement)**
- **What:** Contract with consequences
- **Example:** "99% uptime or 10% refund"

### **Our Pipeline SLOs:**
```
Availability:  99.5% per day
Latency p95:   <15 seconds
Error Rate:    <1% per hour
Data Quality:  >99% records valid
```

---

# 🛠️ PART 2: HANDS-ON (3-4 HOURS)

## ✅ Prerequisites Check

```bash
# 1. Check Docker services running
docker ps | grep -E 'postgres|grafana'

# Should see:
# postgres   Up
# grafana    Up

# 2. Check Silver data exists
ls data/silver/clickstream/_delta_log/

# Should see files (not empty)

# 3. Check free memory (important for 8GB systems!)
free -h

# Should have >2GB available
```

---

## 📊 STEP 1: Create Metrics Schema (15 minutes)

### **1.1: Download Schema File**
Download `create_metrics_schema.sql` from the outputs.

### **1.2: Review Schema**
```bash
# Open in editor
nano create_metrics_schema.sql

# OR just view
cat create_metrics_schema.sql | less
```

**Key tables created:**
- `metrics.pipeline_metrics` - Time-series metrics
- `metrics.pipeline_runs` - Job execution history
- `metrics.data_quality_checks` - DQ results
- `metrics.system_resources` - CPU/memory
- `metrics.business_metrics` - Revenue, conversion
- `metrics.alerts` - Alert history

### **1.3: Execute Schema Creation**
```bash
# Method 1: Direct psql
docker exec -i postgres psql -U dataeng -d analytics < create_metrics_schema.sql

# Method 2: Interactive
docker exec -it postgres psql -U dataeng -d analytics

# Then paste SQL or:
\i /path/to/create_metrics_schema.sql
```

### **1.4: Verify Tables Created**
```bash
docker exec -it postgres psql -U dataeng -d analytics

# List metrics tables
\dt metrics.*

# Should show:
# metrics.pipeline_metrics
# metrics.pipeline_runs
# metrics.data_quality_checks
# metrics.system_resources
# metrics.business_metrics
# metrics.alerts

# Check sample data
SELECT * FROM metrics.pipeline_metrics LIMIT 5;

# Exit
\q
```

**✅ Checkpoint:** You should see 6 tables in metrics schema with sample data.

---

## 📤 STEP 2: Export Metrics from Spark (30 minutes)

### **2.1: Understand Metrics Export Flow**
```
Spark Delta Lake → Python Script → PostgreSQL → Grafana
```

**What we export:**
1. Pipeline metrics (events processed, rates)
2. Business metrics (conversion rates, revenue)
3. Data quality metrics (null checks, validations)
4. System metrics (Docker CPU/memory)

### **2.2: Download Export Script**
Download `export_metrics_complete.py` from outputs.

### **2.3: Review Script**
```bash
# View the script
cat export_metrics_complete.py | less

# Key functions:
# - export_pipeline_metrics()   → Events, rates
# - export_business_metrics()   → Conversion, revenue
# - export_data_quality_metrics() → DQ checks
# - export_system_metrics()     → CPU/memory
```

### **2.4: Run Metrics Export**
```bash
cd ~/data-engineering-projects/ecommerce-streaming-platform-uv

# Run export
python3 export_metrics_complete.py
```

**Expected output:**
```
⚡ Initializing Spark...
🔌 Connecting to PostgreSQL...

📊 Exporting Pipeline Metrics...
✅ Total events: 16,783
✅ page_view: 11,349
✅ search: 2,605
✅ Events in last hour: 450
✅ Event rate: 0.13 events/sec

💰 Exporting Business Metrics...
✅ View → Search: 23.0%
✅ Search → Cart: 62.4%
✅ Overall Conversion: 4.0%
✅ Total Revenue: $125,487.50

✅ Exporting Data Quality Metrics...
✅ Null check user_id: passed (0/16783)
✅ Event type validation: passed (0 invalid)

💻 Exporting System Metrics...
✅ System metrics exported

✅ METRICS EXPORT COMPLETE
   Duration: 42.3 seconds
   Total events processed: 16,783
```

### **2.5: Verify Metrics in PostgreSQL**
```bash
docker exec -it postgres psql -U dataeng -d analytics

-- Check pipeline metrics
SELECT metric_name, metric_value, recorded_at 
FROM metrics.pipeline_metrics 
ORDER BY recorded_at DESC 
LIMIT 10;

-- Check business metrics
SELECT * FROM metrics.latest_metrics 
WHERE metric_name LIKE 'business.%';

-- Check pipeline health
SELECT * FROM metrics.pipeline_health;

-- Exit
\q
```

**✅ Checkpoint:** Metrics tables populated with recent data.

---

## 📊 STEP 3: Configure Grafana (45 minutes)

### **3.1: Access Grafana**
```bash
# Check Grafana is running
docker ps | grep grafana

# If not running:
docker compose -f docker/docker-compose.yml up -d grafana
```

**Open browser:**
```
http://localhost:3001
```

**Login:**
- Username: `admin`
- Password: `admin123`

(You may be asked to change password - skip or set new one)

---

### **3.2: Add PostgreSQL Data Source**

**Step 1:** Click "⚙️ Configuration" (gear icon) → "Data Sources"

**Step 2:** Click "Add data source"

**Step 3:** Search for and select "PostgreSQL"

**Step 4:** Fill in connection details:
```
Name:          Analytics PostgreSQL
Host:          postgres:5432
Database:      analytics
User:          dataeng
Password:      dataeng123
TLS/SSL Mode:  disable
Version:       15.0
```

**IMPORTANT:** Use `postgres` as hostname (not `localhost`)!
This is the Docker container name.

**Step 5:** Scroll down, click "Save & Test"

**Expected:** ✅ "Database Connection OK"

**If error:** Check that PostgreSQL container is running and accessible.

---

### **3.3: Import Dashboard**

**Method 1: Import from JSON (Recommended)**

1. Download `grafana_dashboard.json`

2. In Grafana: Click "+" → "Import"

3. Click "Upload JSON file" → Select `grafana_dashboard.json`

4. Select datasource: "Analytics PostgreSQL"

5. Click "Import"

**✅ Dashboard loaded!**

---

**Method 2: Create Dashboard Manually**

If JSON import fails, create panels manually:

#### **Panel 1: Total Events (Big Number)**

1. Click "+" → "Add panel"

2. Select visualization: "Stat"

3. In query editor:
   - Select datasource: "Analytics PostgreSQL"
   - Format: Table
   - SQL:
     ```sql
     SELECT metric_value 
     FROM metrics.latest_metrics 
     WHERE metric_name = 'pipeline.events.total' 
     LIMIT 1
     ```

4. In panel options (right side):
   - Title: "Total Events Processed"
   - Graph mode: None
   - Color mode: Background
   - Unit: Short

5. Thresholds:
   - 0: Green
   - 10000: Yellow
   - 50000: Red

6. Click "Apply"

---

#### **Panel 2: Event Rate (Stat with Graph)**

1. Add new panel

2. Visualization: "Stat"

3. Query:
   ```sql
   SELECT metric_value 
   FROM metrics.latest_metrics 
   WHERE metric_name = 'pipeline.events.rate' 
   LIMIT 1
   ```

4. Options:
   - Title: "Event Processing Rate"
   - Graph mode: Area
   - Unit: ops (operations per second)
   - Decimals: 2

5. Thresholds:
   - 0: Red
   - 10: Yellow
   - 40: Green

---

#### **Panel 3: Conversion Rate (Gauge)**

1. Add panel

2. Visualization: "Gauge"

3. Query:
   ```sql
   SELECT metric_value 
   FROM metrics.latest_metrics 
   WHERE metric_name = 'business.conversion.overall' 
   LIMIT 1
   ```

4. Options:
   - Title: "Overall Conversion Rate"
   - Min: 0
   - Max: 10
   - Unit: percent (0-100)

5. Thresholds:
   - 0: Red
   - 2: Yellow
   - 4: Green

---

#### **Panel 4: Events Over Time (Time Series)**

1. Add panel

2. Visualization: "Time series"

3. Query:
   ```sql
   SELECT 
     recorded_at as time,
     metric_value as value
   FROM metrics.pipeline_metrics 
   WHERE metric_name = 'pipeline.events.total'
     AND recorded_at > NOW() - INTERVAL '24 hours'
   ORDER BY time
   ```

4. Format: "Time series"

5. Options:
   - Title: "Events Over Time (24h)"
   - Line interpolation: Smooth
   - Fill opacity: 10%

---

#### **Panel 5: Events by Type (Pie Chart)**

1. Add panel

2. Visualization: "Pie chart"

3. Query:
   ```sql
   SELECT 
     tags->>'event_type' as event_type,
     MAX(metric_value) as count
   FROM metrics.pipeline_metrics 
   WHERE metric_name = 'pipeline.events.by_type'
     AND recorded_at > NOW() - INTERVAL '1 hour'
   GROUP BY tags->>'event_type'
   ORDER BY count DESC
   ```

4. Options:
   - Title: "Events by Type"
   - Legend: Table, Right placement
   - Pie type: Pie

---

#### **Panel 6: Pipeline Runs Table**

1. Add panel

2. Visualization: "Table"

3. Query:
   ```sql
   SELECT 
     pipeline_name,
     status,
     duration_seconds,
     events_processed,
     started_at
   FROM metrics.pipeline_runs 
   ORDER BY started_at DESC 
   LIMIT 10
   ```

4. Format: "Table"

5. Field overrides:
   - Column "status": Display mode → Color background
   - Value mappings:
     - success → ✅ (green)
     - failed → ❌ (red)
     - running → ⏳ (blue)

---

### **3.4: Save Dashboard**

1. Click "💾 Save dashboard" (disk icon, top right)

2. Name: "E-Commerce Pipeline Monitoring"

3. Add description: "Real-time monitoring of data pipeline health and performance"

4. Click "Save"

---

### **3.5: Set Auto-Refresh**

1. In dashboard, click refresh dropdown (top right)

2. Select "30s" (refresh every 30 seconds)

3. Dashboard now updates automatically!

---

## 🚨 STEP 4: Create Alerts (30 minutes)

### **4.1: Create Alert for High Error Rate**

1. Edit "Event Processing Rate" panel

2. Click "Alert" tab

3. Create alert rule:
   - Name: "High Error Rate"
   - Condition: `WHEN last() OF query(A) IS BELOW 10`
   - Evaluate every: 1m
   - For: 5m

4. Add notification:
   - Channel: Default (email)
   - Message: "Event processing rate dropped below 10 events/sec"

5. Save

---

### **4.2: Create Alert for Failed Pipeline**

1. Create new panel with query:
   ```sql
   SELECT COUNT(*) as failed_runs
   FROM metrics.pipeline_runs
   WHERE status = 'failed'
     AND started_at > NOW() - INTERVAL '1 hour'
   ```

2. Add alert:
   - Condition: `WHEN last() IS ABOVE 0`
   - Message: "Pipeline run failed in last hour"

---

### **4.3: Configure Notification Channel (Optional)**

1. Go to "Alerting" → "Notification channels"

2. Add channel:
   - Type: Email
   - Addresses: your-email@example.com
   - OR use Slack webhook
   - OR PagerDuty

3. Test notification

---

## 📈 STEP 5: Advanced Dashboards (30 minutes)

### **5.1: Create Business Dashboard**

Create separate dashboard for stakeholders:

**Panels:**
1. **Total Revenue** (Big number)
2. **Conversion Funnel** (Bar chart)
3. **Top Products** (Table)
4. **Revenue Trend** (Time series)
5. **Active Users** (Stat)

**Queries:**
```sql
-- Total Revenue
SELECT SUM(metric_value) 
FROM metrics.business_metrics 
WHERE metric_name = 'business.revenue.total'

-- Conversion Funnel
SELECT 
  SUBSTRING(metric_name FROM 18) as stage,
  MAX(metric_value) as value
FROM metrics.pipeline_metrics
WHERE metric_name LIKE 'business.funnel.%'
GROUP BY metric_name
ORDER BY value DESC
```

---

### **5.2: Create Data Quality Dashboard**

**Panels:**
1. **DQ Pass Rate** (Gauge)
2. **Failed Checks** (Table)
3. **Null Detection Trend** (Time series)
4. **Check Status by Dataset** (Bar chart)

**Query:**
```sql
-- DQ Pass Rate
SELECT 
  (COUNT(*) FILTER (WHERE status = 'passed')::float / COUNT(*) * 100) as pass_rate
FROM metrics.data_quality_checks
WHERE checked_at > NOW() - INTERVAL '24 hours'

-- Failed Checks
SELECT 
  check_name,
  status,
  failure_rate,
  records_failed,
  checked_at
FROM metrics.data_quality_checks
WHERE status IN ('warning', 'failed')
ORDER BY checked_at DESC
LIMIT 10
```

---

## 🎯 PART 3: VERIFICATION & TESTING (30 minutes)

### **Test 1: Generate New Data**

```bash
# Terminal 1: Run data generator for 5 minutes
cd ~/data-engineering-projects/ecommerce-streaming-platform-uv
timeout 300 python3 -m data_generator.run_generator

# Terminal 2: Run Bronze streaming
timeout 180 python3 streaming/kafka_to_bronze.py

# Wait, then process
python3 streaming/bronze_to_silver.py

# Export new metrics
python3 export_metrics_complete.py
```

**In Grafana:** Watch dashboard update in real-time!

---

### **Test 2: Verify Metrics Accuracy**

```bash
# Check actual event count in Delta Lake
python3 << 'EOF'
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("verify").getOrCreate()
silver = spark.read.format("delta").load("data/silver/clickstream")
print(f"Silver events: {silver.count():,}")
spark.stop()
EOF

# Check metric in PostgreSQL
docker exec -it postgres psql -U dataeng -d analytics -c \
  "SELECT metric_value FROM metrics.latest_metrics WHERE metric_name = 'pipeline.events.total';"

# Numbers should match!
```

---

### **Test 3: Alert Testing**

```bash
# Simulate failure by inserting failed pipeline run
docker exec -it postgres psql -U dataeng -d analytics

INSERT INTO metrics.pipeline_runs 
(pipeline_name, run_id, status, duration_seconds)
VALUES ('test_pipeline', 'test_001', 'failed', 0);

# Wait 5-10 minutes
# Check Grafana → Alerting
# Should show firing alert
```

---

## 🎓 PART 4: INTERVIEW PREPARATION

### **Question 1: Explain Your Monitoring Architecture**

**Answer:**
"I implemented a metrics-based monitoring solution using PostgreSQL as the time-series store and Grafana for visualization. Spark jobs export metrics to PostgreSQL's metrics schema after each run - covering pipeline health, data quality, and business KPIs. Grafana queries PostgreSQL and displays metrics in real-time dashboards with 30-second refresh. This architecture provides visibility into system health and enables data-driven operational decisions."

---

### **Question 2: What Metrics Do You Monitor?**

**Answer:**
"I follow the 4 Golden Signals approach:
1. **Latency** - p95 processing time from Kafka to Silver layer
2. **Traffic** - Events processed per second
3. **Errors** - Failed Spark tasks and data quality violations
4. **Saturation** - Executor memory and CPU utilization

Additionally, I track business metrics like conversion rate (4%) and revenue, plus data quality metrics including null detection and schema validation pass rates."

---

### **Question 3: How Do You Handle Alerts?**

**Answer:**
"I use severity-based alerting with 3 levels:
- **Critical** (P1): Pipeline down, no events in 10 minutes → page immediately
- **Warning** (P2): Error rate > 5% for 15 minutes → ticket
- **Info** (P3): Slow query detected → log only

I avoid alert fatigue by alerting on symptoms that impact users, not every system state change. Each alert includes context (current value, threshold, runbook link) to enable quick triage."

---

### **Question 4: Explain SLOs vs SLAs**

**Answer:**
"SLI is the metric itself - like '95% of events processed in under 10 seconds.' SLO is our internal target - like '99.5% availability per day.' SLA is the customer-facing contract with consequences - like '99% uptime or we refund 10%.'

For our pipeline, I set SLOs at 99.5% availability and p95 latency under 15 seconds. These are tracked in Grafana and used to calculate error budget. If we consume 50% of monthly error budget, we slow down feature releases to improve stability."

---

### **Question 5: Dashboard Design Principles?**

**Answer:**
"I follow the 5-second rule - can someone understand system health in 5 seconds? This means:
- Big numbers for key metrics (16,783 events processed)
- Color coding (green/yellow/red) for status
- Time-series graphs for trends
- Minimal text, maximum signal

I create different dashboards for different audiences: executives get high-level KPIs, operations get system health, engineers get detailed performance metrics. Each dashboard has a clear purpose and actionable information."

---

## 🐛 TROUBLESHOOTING

### **Issue 1: "Database connection failed" in Grafana**

**Cause:** Wrong hostname or credentials

**Fix:**
```bash
# Use 'postgres' not 'localhost'
Host: postgres:5432

# Verify PostgreSQL is accessible
docker exec -it grafana ping postgres

# Check credentials
docker exec -it postgres psql -U dataeng -d analytics -c "SELECT 1;"
```

---

### **Issue 2: "No data" in panels**

**Cause:** Metrics not exported yet

**Fix:**
```bash
# Run export script
python3 export_metrics_complete.py

# Verify data in PostgreSQL
docker exec -it postgres psql -U dataeng -d analytics -c \
  "SELECT COUNT(*) FROM metrics.pipeline_metrics;"

# Should return > 0
```

---

### **Issue 3: Slow dashboard loading**

**Cause:** Too much data, missing indexes

**Fix:**
```sql
-- Add indexes (already in schema, but verify)
CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_name_time 
  ON metrics.pipeline_metrics(metric_name, recorded_at DESC);

-- Limit query time range
WHERE recorded_at > NOW() - INTERVAL '24 hours'

-- Use views for complex queries
SELECT * FROM metrics.pipeline_health;
```

---

### **Issue 4: Metrics export fails**

**Cause:** Spark out of memory (8GB systems)

**Fix:**
```bash
# Use LOW_MEMORY config
# streaming/utils/spark_session.py should have:
.config("spark.driver.memory", "512m")

# OR export smaller time windows
# Modify export script to process data in batches
```

---

## ✅ COMPLETION CHECKLIST

- [ ] Metrics schema created in PostgreSQL (6 tables)
- [ ] Metrics export script runs successfully
- [ ] Metrics visible in PostgreSQL
- [ ] Grafana connected to PostgreSQL
- [ ] Dashboard created with 8+ panels
- [ ] Dashboard auto-refreshes
- [ ] At least 1 alert configured
- [ ] Tested with new data generation
- [ ] Metrics match actual data
- [ ] Can explain architecture in interview

---

## 🎉 CONGRATULATIONS!

You've built a production-grade monitoring system!

**What you achieved:**
- ✅ Time-series metrics storage
- ✅ Real-time dashboards
- ✅ Automated alerting
- ✅ Business KPI tracking
- ✅ Data quality monitoring
- ✅ Interview-ready knowledge

**Next steps:**
1. Create additional dashboards (business, DQ)
2. Set up email/Slack notifications
3. Implement anomaly detection
4. Add dashboard screenshots to portfolio
5. Practice explaining to others

---

## 📚 ADDITIONAL RESOURCES

**Grafana Documentation:**
- https://grafana.com/docs/grafana/latest/
- Panel types: https://grafana.com/docs/grafana/latest/panels/
- Alerting: https://grafana.com/docs/grafana/latest/alerting/

**Metrics Best Practices:**
- Google SRE Book: https://sre.google/sre-book/monitoring-distributed-systems/
- Prometheus naming: https://prometheus.io/docs/practices/naming/

**SQL for Time-Series:**
- Window functions: https://www.postgresql.org/docs/current/functions-window.html
- Time-series queries: https://www.timescale.com/blog/sql-queries-for-time-series-analysis/

---

**Total Time Invested:** 4-6 hours  
**Value Created:** Production monitoring system  
**Interview Impact:** Demonstrates senior-level ops knowledge

**You're now a monitoring expert!** 🎯📊
