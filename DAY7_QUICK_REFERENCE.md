# 📊 DAY 7 QUICK REFERENCE

## ⚡ QUICK START (15 MINUTES)

```bash
# 1. Create metrics schema
docker exec -i postgres psql -U dataeng -d analytics < create_metrics_schema.sql

# 2. Export metrics
python3 export_metrics_complete.py

# 3. Access Grafana
http://localhost:3001
Login: admin / admin123

# 4. Add datasource
Configuration → Data Sources → Add → PostgreSQL
Host: postgres:5432
Database: analytics
User: dataeng
Password: dataeng123

# 5. Import dashboard
+ → Import → Upload grafana_dashboard.json
```

---

## 📊 KEY SQL QUERIES

### **Latest Metrics**
```sql
SELECT * FROM metrics.latest_metrics;
```

### **Pipeline Health (24h)**
```sql
SELECT * FROM metrics.pipeline_health;
```

### **Active Alerts**
```sql
SELECT * FROM metrics.active_alerts;
```

### **Events Over Time**
```sql
SELECT recorded_at, metric_value 
FROM metrics.pipeline_metrics 
WHERE metric_name = 'pipeline.events.total'
  AND recorded_at > NOW() - INTERVAL '24 hours'
ORDER BY recorded_at;
```

### **Conversion Funnel**
```sql
SELECT 
  SUBSTRING(metric_name FROM 18) as stage,
  MAX(metric_value) as count
FROM metrics.pipeline_metrics
WHERE metric_name LIKE 'business.funnel.%'
GROUP BY metric_name
ORDER BY count DESC;
```

---

## 🎨 GRAFANA PANEL TYPES

| Metric | Visualization |
|--------|--------------|
| Single number | Stat |
| Trend over time | Time series |
| Distribution | Histogram |
| Comparison | Bar chart |
| Percentage | Gauge |
| Categories | Pie chart |
| Details | Table |

---

## 🚨 ALERT THRESHOLDS

```
Event Rate:
  < 10/sec     → Critical
  10-40/sec    → Warning
  > 40/sec     → Normal

Conversion Rate:
  < 2%         → Critical
  2-4%         → Warning
  > 4%         → Normal

Pipeline Success:
  < 95%        → Critical
  95-99%       → Warning
  > 99%        → Normal
```

---

## 📈 METRICS NAMING

**Format:** `namespace.metric.aggregation`

**Examples:**
```
pipeline.events.total
pipeline.events.rate
pipeline.latency.p95
business.conversion.overall
business.revenue.total
```

---

## 🎯 4 GOLDEN SIGNALS

1. **Latency** - How long? (p95 latency)
2. **Traffic** - How much? (events/sec)
3. **Errors** - What's failing? (error rate)
4. **Saturation** - How full? (memory %)

---

## 🔧 TROUBLESHOOTING

**No data in panels:**
```bash
# Export metrics
python3 export_metrics_complete.py

# Verify in PostgreSQL
docker exec -it postgres psql -U dataeng -d analytics -c \
  "SELECT COUNT(*) FROM metrics.pipeline_metrics;"
```

**Grafana connection failed:**
```
Use: postgres:5432 (not localhost:5432)
```

**Dashboard slow:**
```sql
-- Limit time range
WHERE recorded_at > NOW() - INTERVAL '24 hours'

-- Use indexes
CREATE INDEX ... (already in schema)
```

---

## 📊 EXPORT METRICS COMMANDS

```bash
# Full export
python3 export_metrics_complete.py

# Check what was exported
docker exec -it postgres psql -U dataeng -d analytics

SELECT metric_name, COUNT(*) 
FROM metrics.pipeline_metrics 
GROUP BY metric_name;
```

---

## 🎓 INTERVIEW ANSWERS

**Q: What do you monitor?**
> "I follow the 4 Golden Signals: latency (p95 processing time), traffic (events/sec), errors (failed tasks), and saturation (memory usage). Plus business metrics like 4% conversion rate."

**Q: Why Grafana?**
> "Grafana provides real-time visualization, supports multiple datasources, has rich panel types, and includes built-in alerting. It's industry-standard for observability."

**Q: How do you alert?**
> "Severity-based: P1 for pipeline down (page immediately), P2 for degraded performance (ticket), P3 for info (log only). Alert on user impact, not every state change."

---

## 📋 COMPLETION CHECKLIST

- [ ] Metrics schema created
- [ ] Metrics export runs
- [ ] Grafana connected
- [ ] Dashboard created
- [ ] Auto-refresh enabled
- [ ] At least 1 alert set
- [ ] Tested with new data
- [ ] Can explain in interview

---

## 🚀 NEXT STEPS

1. Create business dashboard
2. Set up Slack/email alerts
3. Add more panels (system resources)
4. Implement anomaly detection
5. Screenshot for portfolio
6. Practice explaining

---

**Duration:** 4-6 hours  
**Difficulty:** Intermediate  
**Value:** Production monitoring system  

**You're now a monitoring expert!** 🎯
