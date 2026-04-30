# Data Quality Framework - 7 Great Expectations Suites

## Overview

This document describes the comprehensive data quality validation framework implemented using Great Expectations. The framework implements **7 distinct quality suites** that validate data across the ecommerce streaming platform's Bronze → Silver → Gold pipeline.

**Key Features:**
- ✅ Schema validation at column and type level
- ✅ Null checks on critical fields
- ✅ Range constraints on numeric values
- ✅ Set membership for categorical fields
- ✅ Uniqueness checks for business keys
- ✅ Referential integrity validation
- ✅ Completeness and freshness monitoring
- 🔐 **Gold layer write gate** - Blocks writes until quality gates pass
- 📊 **Data docs** - JSON reports for visibility into quality trends
- 🚨 **Alert triggers** - Failures documented for review/remediation

---

## The 7 Great Expectations Suites

### Suite 1: Schema Validation
**Purpose:** Ensure data structure conformity and type consistency

**What it checks:**
- Column existence: All required columns present
- Data types: Columns have expected types
- No unexpected schema changes

**Critical Columns Validated:**
- `user_id` (object/string)
- `event_type` (object/string)
- `timestamp` (datetime64)
- `session_id` (object/string)
- `device_type` (object/string)

**Example Expectations:**
```
✅ column_user_id_exists_with_type_object
✅ column_event_type_exists_with_type_object
✅ column_timestamp_exists_with_type_datetime64[ns]
✅ column_session_id_exists_with_type_object
✅ column_device_type_exists_with_type_object
```

**Failure Impact:** CRITICAL - Blocks Gold writes
**Remediation:** Check for upstream schema changes in Silver layer

---

### Suite 2: Null Checks
**Purpose:** Validate required fields don't contain missing values

**What it checks:**
- No NULL values in critical business columns
- Data completeness percentages
- Null distribution patterns

**Validated Columns:**
- `user_id` - Must have user identifier
- `event_type` - Must classify event
- `timestamp` - Must record event timing
- `session_id` - Must link events to sessions

**Example Expectations:**
```
✅ no_nulls_user_id: 0 nulls (0.00%)
✅ no_nulls_event_type: 0 nulls (0.00%)
✅ no_nulls_timestamp: 0 nulls (0.00%)
✅ no_nulls_session_id: 0 nulls (0.00%)
```

**Failure Impact:** CRITICAL - Blocks Gold writes
**Remediation:** Fix data pipeline to drop/impute nulls before Silver layer

---

### Suite 3: Range Constraints
**Purpose:** Verify numeric values are within acceptable business ranges

**What it checks:**
- Price values within 0-10,000 range
- Quantity values within 1-1,000 range
- No phantom values (negative prices, zero quantities)

**Validated Columns:**
- `price` - Product prices
- `quantity` - Order quantities

**Example Expectations:**
```
✅ range_price_0_to_10000: 1000 in range, 0 out
✅ range_quantity_1_to_1000: 1000 in range, 0 out
```

**Failure Impact:** NON-CRITICAL - Advisory warning
**Remediation:** Investigate data spikes; check for data entry errors; may require business review

---

### Suite 4: Set Membership
**Purpose:** Enforce categorical domain constraints (enums)

**What it checks:**
- `event_type` values are from defined set
- `device_type` values are legitimate
- No unexpected/typo'd enum values

**Valid Value Sets:**
```
event_type: {page_view, search, add_to_cart, checkout_started, checkout_completed, purchase}
device_type: {mobile, desktop, tablet}
```

**Example Expectations:**
```
✅ set_membership_event_type: 1000 valid, 0 invalid
✅ set_membership_device_type: 1000 valid, 0 invalid
```

**Failure Impact:** CRITICAL - Blocks Gold writes
**Remediation:** Check upstream data transformations; validate enum mapping in Silver layer

---

### Suite 5: Uniqueness Checks
**Purpose:** Validate business key distribution and expected patterns

**What it checks:**
- Multiple events per user expected (duplication OK)
- Multiple events per session expected
- Ratio of unique values vs total records
- Business logic compliance for keying

**Validated Columns:**
- `user_id` - Expected duplicates (95% duplication rate OK)
- `session_id` - Expected duplicates (90% duplication rate OK)

**Example Expectations:**
```
✅ uniqueness_user_id: 50 unique, duplication: 95.0%
   Multiple events per user expected
✅ uniqueness_session_id: 100 unique, duplication: 90.0%
   Multiple events per session expected
```

**Failure Impact:** NON-CRITICAL - Advisory warning
**Remediation:** May indicate missing user/session data; check upstream aggregation

---

### Suite 6: Referential Integrity
**Purpose:** Validate relationships and logical consistency

**What it checks:**
- Each session belongs to exactly one user
- All records have timestamps
- Session-user mappings are consistent
- No orphaned foreign keys

**Example Expectations:**
```
✅ session_has_user_id: Sessions with multiple users: 0/100
   Each session belongs to exactly one user
✅ all_rows_timestamped: Null timestamps: 0/1000
   All records have timestamp values
```

**Failure Impact:** CRITICAL - Blocks Gold writes
**Remediation:** Review user-session assignment logic; fix any multi-user sessions

---

### Suite 7: Completeness & Freshness
**Purpose:** Monitor data staleness and overall quality coverage

**What it checks:**
- Data age (freshness < 1 hour)
- Overall null percentage (completeness ≥ 95%)
- Time since last update
- Data readiness for analytics

**Example Expectations:**
```
✅ data_freshness_1hour: Latest data: 2026-04-07 16:39:00, Age: 4:23:54.856816
✅ data_completeness_95_percent: Completeness score: 100.00%
```

**Failure Impact:** CRITICAL - Blocks Gold writes
**Remediation:** 
- Freshness failure: Check upstream data ingestion; ensure daily/hourly loads
- Completeness failure: Increase null handling in transformations

---

## Gold Layer Write Gate

The **Gold Layer Guard** prevents writes until all critical quality gates pass.

### Critical vs Advisory Gates

| Suite | Criticality | Blocks Gold | Blocks Analytics |
|-------|-------------|-------------|-----------------|
| Schema Validation | 🔴 CRITICAL | Yes | Yes |
| Null Checks | 🔴 CRITICAL | Yes | Yes |
| Range Constraints | 🟡 ADVISORY | No | No |
| Set Membership | 🔴 CRITICAL | Yes | Yes |
| Uniqueness Checks | 🟡 ADVISORY | No | No |
| Referential Integrity | 🔴 CRITICAL | Yes | Yes |
| Completeness & Freshness | 🔴 CRITICAL | Yes | Yes |

### Usage in Gold Layer

```python
from streaming.gold_layer_guard import check_gold_layer_approval

# In your silver_to_gold.py stream:
if not check_gold_layer_approval():
    raise Exception("Quality gates failed - Gold write blocked")

# Safe to write to Gold
df.write.format("delta").mode("append").save("data/gold/...")
```

---

## Data Docs & Reports

Quality assessments are documented in structured JSON reports.

**Report Location:** `data_quality/reports/data_quality_report_YYYYMMDD_HHMMSS.json`

**Report Structure:**
```json
{
  "timestamp": "2026-04-07T21:02:54.xxx",
  "total_suites": 7,
  "suites": [
    {
      "suite_name": "schema_validation",
      "expectations": [
        {
          "name": "column_user_id_exists_with_type_object",
          "passed": true,
          "details": "..."
        }
      ],
      "passed": 5,
      "failed": 0
    }
  ],
  "summary": {
    "total_expectations": 19,
    "total_passed": 18,
    "total_failed": 1,
    "suites_passed": 6,
    "suites_failed": 1
  }
}
```

**Trend Visibility:**
- Historical reports enable trend analysis
- Quality degradation detection
- SLA compliance tracking
- Data pipeline health monitoring

---

## Running Validation

### Command Line
```bash
# From project root
python3 data_quality/validate_data.py

# Output includes:
# - 7 suite summaries with per-expectation details
# - Pass/fail counts
# - JSON report generation
# - Gold layer write gate decision
```

### Programmatic Access

```python
from spark_session import get_spark_session
from data_quality.validate_data import run_validation, generate_data_docs

spark = get_spark_session("DataQuality")
df = spark.read.format("delta").load("data/silver/clickstream")

# Run all 7 suites
all_suites = run_validation(spark, df)

# Generate docs
report = generate_data_docs(all_suites)

# Check Gold readiness
from streaming.gold_layer_guard import check_gold_layer_approval
approved = check_gold_layer_approval()
```

---

## Alert Triggers

Quality failures generate alerts for:

1. **Schema Changes** (Suite 1)
   - Alert: New/removed columns
   - Action: Update downstream schemas

2. **Missing Data** (Suite 2)
   - Alert: Null counts exceed threshold
   - Action: Investigate upstream pipeline

3. **Data Out of Bounds** (Suite 3)
   - Alert: Prices/quantities exceed ranges
   - Action: Data quality review

4. **Invalid Enums** (Suite 4)
   - Alert: Unknown event/device types
   - Action: Enum mapping validation

5. **Key Distribution** (Suite 5)
   - Alert: Unexpected uniqueness patterns
   - Action: Aggregation logic check

6. **Broken Relationships** (Suite 6)
   - Alert: Multi-user sessions detected
   - Action: User-session mapping fix

7. **Stale Data** (Suite 7)
   - Alert: Data older than 1 hour
   - Action: Ingestion pipeline restart

---

## Implementation Details

### File Structure
```
data_quality/
  ├── validate_data.py          # Main validation engine (7 suites)
  └── reports/
      └── data_quality_report_*.json  # Historical reports

streaming/
  └── gold_layer_guard.py       # Write gate enforcement
```

### Dependencies
- `great_expectations` - Quality framework
- `pandas` - Data manipulation  
- `pyspark` - Spark integration
- `numpy` - Synthetic data generation

### Configuration
All validations are self-contained in Python code. No external config files required.
Update validation thresholds directly in:
- `data_quality/validate_data.py` for quality rules
- `streaming/gold_layer_guard.py` for gate criticality

---

## Next Steps

1. **Integrate with Orchestration:**
   - Add quality check as DAG task in Airflow/Databricks
   - Run before Gold layer writes
   - Fail pipeline on critical failures

2. **Enable Monitoring:**
   - Track quality metrics over time
   - Dashboard for Pass/Fail rates
   - Alerting on degradation

3. **Automate Remediation:**
   - Automatic retries on transient failures
   - Data quarantine for quality issues
   - Alert escalation for critical gaps

4. **Expand Validation:**
   - Add business logic checks (e.g., conversion rates)
   - Anomaly detection (statistical outliers)
   - Cross-layer consistency checks

---

## Reference

**Great Expectations Documentation:**
- https://docs.greatexpectations.io/
- Badge Support: https://docs.greatexpectations.io/docs/terms/expectation

**Ecommerce Streaming Platform:**
- See: `docs/DAY_1_GUIDE.md` for architecture
- See: `docs/day_2.md` for streaming details
