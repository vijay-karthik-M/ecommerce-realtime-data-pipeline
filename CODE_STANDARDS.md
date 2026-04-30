# CODE STANDARDS & CONVENTIONS

## Comment Guidelines (Industry Standard)

This codebase follows **Google-style Python documentation** with enhanced comments for newcomers.

### Module-Level Docstring

Every `.py` file starts with a module docstring explaining:
- **What**: Purpose of the module
- **Why**: Business context and design decisions
- **How**: High-level flow (readers don't need to dive into code)

```python
#!/usr/bin/env python3
"""
KAFKA TO BRONZE - Real-time Data Ingestion
==========================================

Reads events from Kafka and writes to Delta Lake Bronze layer.

CONCEPTS:
- Structured Streaming from Kafka
- Bronze layer = raw data preservation
- Checkpointing for fault tolerance
- Exactly-once semantics

BRONZE LAYER PHILOSOPHY:
"Store everything, transform nothing"
- Exact copy of source data
- Enables reprocessing if logic changes
- Audit trail of all data received
"""
```

### Function Docstrings (Google Style)

Every function has a docstring with clear structure:

```python
def read_from_kafka(spark: SparkSession, topic: str, use_earliest: bool = True):
    """
    Read streaming data from Kafka topic.
    
    CONCEPT: Kafka Source
    - Treats Kafka as infinite DataFrame
    - Each message = row in DataFrame
    - Columns: key, value, topic, partition, offset, timestamp
    
    EXACTLY-ONCE SEMANTICS:
    - Kafka tracks offsets
    - Spark checkpoints progress
    - On restart, continues from last processed offset
    
    Args:
        spark (SparkSession): Active Spark session
        topic (str): Topic name (clickstream or transactions)
        use_earliest (bool): On first run, read from beginning.
            On restart, checkpoint position overrides this.
            Defaults to True.
    
    Returns:
        DataFrame: Streaming DataFrame with columns [key, value, topic, partition, offset, timestamp]
    
    Raises:
        KafkaTimeoutException: If broker unavailable > 30 seconds
    
    Example:
        df = read_from_kafka(spark, 'clickstream')
        df.show()
    
    Note:
        - Checkpoint recovery automatic (no manual offset tracking)
        - maxOffsetsPerTrigger limits throughput (important on 8GB laptops)
    """
```

### Inline Comments (Explaining Why, Not What)

Comments explain **business logic**, **surprising patterns**, **gotchas**.

```python
def write_to_bronze(df, topic: str, checkpoint_location: str):
    # Add ingestion metadata (no JSON parsing - preserve raw data)
    # Why? Bronze should be immutable mirror of Kafka
    # If Silver logic changes, we can reprocess from Bronze
    bronze_df = (df
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_topic", col("topic"))
        ...
    )
    
    query = (bronze_df
        .writeStream
        .format("parquet")
        .outputMode("append")
        
        .option("checkpointLocation", checkpoint_location)
        .option("path", f"{BRONZE_PATH}/{topic}")
        .partitionBy("ingestion_date")
        
        # Faster trigger for visibility (5 seconds)
        # Tradeoff: 5s latency vs. lower overhead
        # Increase to 30s for production (smoother batching)
        .trigger(processingTime="5 seconds")
        
        .queryName(f"Bronze_{topic}")
        
        .start()
    )
```

### Section Headers (Organize Complex Functions)

Long functions use section headers to separate concerns:

```python
def populate_initial_data(conn):
    """Populate metrics tables with sample data."""
    
    # ===== LOAD GOLD LAYER DATA =====
    gold_files = glob.glob("data/gold/hourly_metrics/**/*.parquet", recursive=True)
    df = pd.concat([pd.read_parquet(f) for f in gold_files], ignore_index=True)
    
    # ===== POPULATE PIPELINE_RUNS =====
    for i in range(1, 6):
        cur.execute("""INSERT INTO ...""")
    
    # ===== POPULATE DATA_QUALITY_CHECKS =====
    for check_name, status in checks:
        cur.execute("""INSERT INTO ...""")
```

## Naming Conventions

### Constants (UPPERCASE)

Configuration values that don't change during execution:

```python
# ✅ Good: Configuration constants
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
BRONZE_PATH = os.path.join(...)
DB_CONFIG = {'host': 'localhost', ...}

# ❌ Bad: Mutable configurations (use lowercase)
# ENV_VARIABLE = "development"  # Could change, use lowercase
```

### Variables (lowercase_with_underscores)

```python
# ✅ Good: Snake case for clarity
total_events = 5577862
current_timestamp = datetime.now()
is_quality_check_passed = True
max_retries = 3

# ❌ Bad: Camel case (not Pythonic)
totalEvents = 5577862
currentTimestamp = datetime.now()
```

### DataFrames (df, df_bronze, df_silver)

```python
# ✅ Good: Clear naming
bronze_df = spark.read.parquet(...)
silver_df = bronze_df.select(...).withColumn(...)
gold_df = silver_df.groupBy(...).agg(...)

# ❌ Bad: Non-descriptive
data = spark.read.parquet(...)
result = data.select(...)
```

### Database Connections (conn)

```python
# ✅ Good: Standard abbreviation
conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("SELECT ...")

# ❌ Bad: Overly verbose
database_connection = get_db_connection()
```

## Error Handling Pattern

```python
def read_data():
    """Read data with graceful error handling."""
    try:
        # Main logic
        data = read_parquet(...)
        return data
        
    except FileNotFoundError as e:
        # Specific exception: Use immediately
        print(f"File not found: {e}")
        # Fix or propagate
        raise
        
    except Exception as e:
        # Generic exception: Log with context
        print(f"Unexpected error reading data: {e}")
        import traceback
        traceback.print_exc()
        # Propagate to caller
        raise
```

Pattern:
1. Specific exceptions first (FileNotFoundError, KafkaError, etc.)
2. Generic Exception last (catches all)
3. Always print/log before propagating
4. Don't silently swallow exceptions

## Import Organization

```python
#!/usr/bin/env python3
"""Module docstring."""

# 1. Standard library (alphabetical)
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 2. Third-party libraries (alphabetical)
import pandas as pd
import psycopg2
from kafka import KafkaProducer
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum

# 3. Local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming.utils.spark_session import get_spark_session
from data_generator.schemas import CLICKSTREAM_SCHEMA
```

## Logging & Print Statements

### Development (Use print for quick feedback)
```python
print("✅ Bronze data loaded successfully")
print(f"  Total records: {df.count():,}")
```

### Production (Use logging module)
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Data pipeline started")
logger.warning(f"Quality check {check_name} failed with rate {failure_rate:.1f}%")
logger.error(f"Failed to write to database: {e}")
```

**When to use what**:
- `print()`: Debug output during development
- `logger.info()`: Normal operations ("pipeline started")
- `logger.warning()`: Degraded but recoverable ("retrying connection")
- `logger.error()`: Serious problems ("database down")

## Type Hints (Optional but Recommended)

```python
from typing import Dict, List, Optional, Tuple
from pyspark.sql import DataFrame

def record_metric(
    conn: psycopg2.connection,
    metric_name: str,
    metric_value: float,
    metric_unit: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Record a metric to database.
    
    Args:
        conn: Database connection
        metric_name: Dot-separated name (e.g., 'pipeline.events.total')
        metric_value: Numeric value
        metric_unit: Optional unit ('count', 'percent', 'USD')
        tags: Optional dimensions for filtering
    """
    ...
```

Benefits:
- IDE autocomplete works better
- Catch type errors early (mypy, Pylance)
- Self-documenting code

## Testing & Validation

### Unit Test Pattern

```python
def test_record_metric():
    """Test metric recording to database."""
    # Arrange (setup)
    conn = get_test_db_connection()
    
    # Act (execute)
    record_metric(conn, 'test.metric', 42.5, 'count')
    
    # Assert (verify)
    with conn.cursor() as cur:
        cur.execute("SELECT metric_value FROM metrics.latest_metrics WHERE metric_name = 'test.metric'")
        result = cur.fetchone()
        assert result[0] == 42.5
```

### Integration Test Pattern

```python
def test_kafka_to_bronze_end_to_end():
    """Test complete flow: Kafka → Bronze."""
    # Setup
    spark = get_spark_session("Test")
    producer = KafkaProducer(...)
    
    # Act: Send events
    for i in range(100):
        producer.send('test-topic', {"id": i})
    
    # Act: Run ingestion
    query = read_from_kafka(...).writeStream...
    time.sleep(5)  # Let batches complete
    
    # Assert: Verify data arrived
    bronze_df = spark.read.parquet(BRONZE_PATH)
    assert bronze_df.count() >= 100
```

## Docstring Levels

### Level 1: Newcomer-Friendly (Current Standard)

```python
def get_spark_session(app_name="EcommerceStreaming"):
    """
    Create a stable, optimized Spark session for streaming on 8GB laptops.
    
    This function handles:
    - Memory allocation suitable for laptops
    - Streaming-specific configurations
    - Error handling and graceful shutdown
    - Delta Lake and Kafka source initialization
    
    Args:
        app_name (str): Spark application name shown in UI
    
    Returns:
        SparkSession: Ready for readStream, writeStream, spark.sql()
    
    Examples:
        spark = get_spark_session("KafkaToBronze")
    """
```

### Level 2: Intermediate (For Code Review)

Add implementation notes:

```python
def process_silver_batch(spark):
    """
    Process Bronze to Silver using BATCH mode.
    
    Why BATCH not STREAM here?
    - Simpler than structured streaming
    - Sufficient for 1x daily aggregation job
    - Less resource overhead (for scheduled runs)
    
    Performance: ~30 seconds on 8GB laptop for 1.8M records
    """
```

### Level 3: Advanced (For Maintainers)

Add internal algorithm notes:

```python
def calculate_unique_users(df):
    """
    Calculate unique users per event_type using HyperLogLog cardinality estimation.
    
    Algorithm Choice Rationale:
    - Exact count: O(n) memory, fails at scale
    - HyperLogLog: O(log(log(n))) memory, <1% error
    - Tradeoff: Slight accuracy loss for 1000x memory savings
    
    Error Rate: ~0.81% (tuned with rsd=0.01)
    """
```

## Code Review Checklist

When reviewing code, check:

- [ ] Module docstring explains purpose and design decisions
- [ ] Every function has Google-style docstring with Args/Returns
- [ ] Complex logic has inline comments explaining "why"
- [ ] Error handling is specific and logged
- [ ] Constants are UPPERCASE, variables are lowercase
- [ ] Imports organized (stdlib, third-party, local)
- [ ] Type hints present (optional but recommended)
- [ ] No hardcoded values (use config constants)
- [ ] Performance considerations documented (if complex)

## Common Patterns in This Codebase

### Pattern 1: Idempotent Operations

Most setup scripts can run multiple times safely:

```python
def setup_metrics_table(conn):
    # DROP IF EXISTS allows re-running without manual cleanup
    cur.execute("DROP TABLE IF EXISTS metrics.latest_metrics CASCADE;")
    cur.execute("""CREATE TABLE metrics.latest_metrics (...)""")
```

**Why**: Development-friendly, allows "reset"
**Note**: In production, use migration tools instead (Alembic, Flyway)

### Pattern 2: Resource Cleanup

Always close connections explicitly:

```python
def populate_data(conn):
    try:
        # ... do work ...
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()  # ALWAYS CLOSE
```

### Pattern 3: Defensive Defaults

Functions handle missing dependencies gracefully:

```python
def read_quality_data(spark):
    try:
        # Try Silver layer (preferred)
        return spark.read.format("delta").load("data/silver/...")
    except Exception as e:
        # Fallback: Synthetic test data
        logger.warning(f"Silver not available, using synthetic: {e}")
        return create_synthetic_test_data()
```

---

## Quick Reference

| What | Convention | Example |
|------|-----------|---------|
| Module purpose | Docstring (50-100 words) | "KAFKA TO BRONZE - Real-time..." |
| Function behavior | Google-style docstring | `"""Process data...\n\nArgs:\n...` |
| Why (not what) | Inline comments | `# Preserved raw JSON for replay capability` |
| Constant value | UPPERCASE | `KAFKA_BOOTSTRAP_SERVERS = "..."` |  
| Variable | lowercase_snake | `total_events = 5577862` |
| Large function | Section headers | `# ===== POPULATE RUNS =====` |
| Error | Specific then generic | `except FileNotFoundError... except Exception` |
| Database | `conn` abbreviation | `conn = get_db_connection()` |
| DataFrame | `df_layer` naming | `bronze_df, silver_df, gold_df` |
| Readability | Numbers with comma | `f"{count:,}"` → "5,577,862" |

---

For questions on specific functions, search for the function name in its file or see [ARCHITECTURE.md](ARCHITECTURE.md) for system-wide patterns.
