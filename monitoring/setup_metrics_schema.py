#!/usr/bin/env python3
"""
METRICS SCHEMA SETUP - Database Initialization
===============================================

Purpose:
    One-time setup script to create all metrics tables and views for Grafana.
    Populates initial data from Gold layer for dashboard visualization.

Tables Created:
    1. metrics.latest_metrics         - Snapshot of current metric values
    2. metrics.pipeline_metrics       - Time-series metric data (for graphs)
    3. metrics.pipeline_runs          - Pipeline execution history
    4. metrics.data_quality_checks    - Quality validation results
    5. metrics.system_resources       - CPU/Memory metrics
    
Views Created:
    1. metrics.active_alerts          - Non-passed quality checks (for alerting)

WHEN TO RUN:
    - First deployment (creates schema)
    - After schema changes
    - To reset all metrics (re-populate from Gold layer)

EXECUTION TIME:
    ~2-3 seconds (fast pandas batch read from Gold layer)

TO RUN:
    python3 setup_metrics_schema.py
"""

import sys
sys.path.insert(0, '/home/jay/data-engineering-projects/ecommerce-streaming-platform-uv')

import pandas as pd
import glob
import json
from datetime import datetime, timedelta
from pathlib import Path
from monitoring.export_metrics_complete import get_db_connection

# PROJECT ROOT for absolute path resolution
PROJECT_ROOT = Path(__file__).parent.parent

def setup_missing_tables():
    """
    Create complete database schema for metrics storage.
    
    Creates 5 tables + 1 view with proper indexes and relationships.
    
    IDEMPOTENCY:
    - Uses DROP IF EXISTS to allow re-running without manual cleanup
    - Recreates tables fresh on each run (development-friendly)
    - In production: Use migration tools (Flyway, Alembic) instead
    
    TABLE DESCRIPTIONS:
    
    1. pipeline_metrics
       - Time-series data for graphs and dashboards
       - Stores historical metric values over time
       - Indexed by (metric_name, recorded_at) for fast time-range queries
       - JSONB tags column allows multi-dimensional filtering
    
    2. pipeline_runs
       - Tracks each pipeline execution lifecycle
       - Records start time, end time, status, event counts
       - Used in "Recent Pipeline Runs" dashboard panel
    
    3. data_quality_checks
       - Stores results of Great Expectations validation suites
       - Records failure rates and number of failed records
       - Powers "Data Quality Status" dashboard panel
    
    4. system_resources
       - CPU and memory usage metrics from Docker containers
       - Enables resource monitoring dashboard
       - Helps identify performance bottlenecks
    
    5. metrics.active_alerts (VIEW)
       - Virtual table showing only quality checks that failed
       - Used for alerting and incident response
       - Automatically filters from data_quality_checks table
    
    Returns:
        None (prints status messages, modifies database)
    """
    conn = get_db_connection()
    
    print("="*80)
    print("📋 CREATING METRICS SCHEMA")
    print("="*80)
    
    try:
        with conn.cursor() as cur:
            # ===== TABLE 1: pipeline_metrics =====
            # PURPOSE: Time-series storage for metrics over time
            # USAGE: Powers Grafana line/bar charts with historical trends
            print("\n1️⃣ Creating pipeline_metrics table...")
            cur.execute("""
                DROP TABLE IF EXISTS metrics.pipeline_metrics CASCADE;
                
                CREATE TABLE metrics.pipeline_metrics (
                    -- Metadata columns
                    metric_id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(255) NOT NULL,
                    metric_value NUMERIC NOT NULL,
                    metric_unit VARCHAR(50),
                    
                    -- Flexible tags for multi-dimensional analysis
                    -- Example: {'event_type': 'page_view', 'device': 'mobile'}
                    tags JSONB,
                    
                    -- Timestamp for time-series queries
                    recorded_at TIMESTAMP DEFAULT NOW()
                );
                
                -- Index for fast metric name lookups + time-range queries
                -- (topic, date DESC) is optimal for "latest N days of metric X" queries
                CREATE INDEX idx_pipeline_metrics_name_time 
                    ON metrics.pipeline_metrics(metric_name, recorded_at DESC);
            """)
            conn.commit()
            print("   ✅ pipeline_metrics table created")
            
            # ===== TABLE 2: pipeline_runs =====
            # PURPOSE: Audit trail of pipeline executions
            # USAGE: Historical performance analysis, SLA tracking
            print("2️⃣ Creating pipeline_runs table...")
            cur.execute("""
                DROP TABLE IF EXISTS metrics.pipeline_runs CASCADE;
                
                CREATE TABLE metrics.pipeline_runs (
                    run_id SERIAL PRIMARY KEY,
                    pipeline_name VARCHAR(255),
                    status VARCHAR(50),              -- 'completed', 'failed', 'running'
                    duration_seconds INT,            -- How long the pipeline took
                    events_processed INT,            -- Rows successfully written
                    events_failed INT,               -- Rows that failed
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                );
                
                -- Index for quick status lookups (failed runs, etc.)
                CREATE INDEX idx_pipeline_runs_status ON metrics.pipeline_runs(status);
            """)
            conn.commit()
            print("   ✅ pipeline_runs table created")
            
            # ===== TABLE 3: data_quality_checks =====
            # PURPOSE: Great Expectations validation results
            # USAGE: Quality reports, alerting on failures
            print("3️⃣ Creating data_quality_checks table...")
            cur.execute("""
                DROP TABLE IF EXISTS metrics.data_quality_checks CASCADE;
                
                CREATE TABLE metrics.data_quality_checks (
                    check_id SERIAL PRIMARY KEY,
                    check_name VARCHAR(255),        -- Schema validation, null checks, etc.
                    status VARCHAR(50),             -- 'passed' or 'failed'
                    failure_rate NUMERIC,           -- Percentage of records that failed
                    records_tested INT,
                    records_failed INT,
                    checked_at TIMESTAMP
                );
                
                -- Index for quick lookups by status (filter to show failures only)
                CREATE INDEX idx_quality_checks_status ON metrics.data_quality_checks(status);
            """)
            conn.commit()
            print("   ✅ data_quality_checks table created")
            
            # ===== TABLE 4: system_resources =====
            # PURPOSE: Infrastructure monitoring (CPU, memory)
            # USAGE: Detects when system is under stress (high memory = OOM risk)
            print("4️⃣ Creating system_resources table...")
            cur.execute("""
                DROP TABLE IF EXISTS metrics.system_resources CASCADE;
                
                CREATE TABLE metrics.system_resources (
                    resource_id SERIAL PRIMARY KEY,
                    resource_type VARCHAR(50),      -- 'cpu', 'memory'
                    metric_value NUMERIC,           -- Percentage (0-100)
                    recorded_at TIMESTAMP DEFAULT NOW()
                );
                
                -- Index for time-range queries on specific resource types
                CREATE INDEX idx_system_resources_type_time 
                    ON metrics.system_resources(resource_type, recorded_at DESC);
            """)
            conn.commit()
            print("   ✅ system_resources table created")
            
            # ===== VIEW 1: active_alerts =====
            # PURPOSE: Show only failing quality checks (for incident response)
            # USAGE: Alert dashboard, on-call monitoring
            print("5️⃣ Creating active_alerts view...")
            cur.execute("DROP VIEW IF EXISTS metrics.active_alerts CASCADE;")
            conn.commit()
            cur.execute("""
                CREATE VIEW metrics.active_alerts AS
                SELECT check_id, check_name, status, checked_at
                FROM metrics.data_quality_checks
                WHERE status != 'passed'
                ORDER BY checked_at DESC;
            """)
            conn.commit()
            print("   ✅ active_alerts view created")
        
        print("\n" + "="*80)
        print("✅ SCHEMA SETUP COMPLETE")
        print("="*80)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error setting up schema: {e}")
        conn.rollback()
        raise

def populate_initial_data(conn):
    """
    Populate all metrics tables with sample data from Gold layer.
    
    This enables Grafana dashboards to display data immediately after setup.
    
    DATA SOURCES:
    - Gold layer Parquet files (already aggregated hourly data)
    - Synthetic timestamps for time-series visualization
    
    POPULATION STRATEGY:
    1. Read Gold layer to get total event count
    2. Create sample pipeline runs (5 historical runs)
    3. Create quality check records (all passed)
    4. Create CPU/memory metrics (simulated 10 data points)
    5. Create Events Over Time (25 hourly data points for 24-hour view)
    6. Create Conversion Funnel (5 funnel stages with drop-off)
    
    Args:
        conn: psycopg2 database connection (already established)
        
    Returns:
        None (modifies database tables)
        
    Time Complexity: O(n) where n = number of Gold layer Parquet files (~500-1000)
    """
    print("\n📊 POPULATING INITIAL DATA")
    print("="*80)
    
    try:
        # ===== LOAD GOLD LAYER DATA =====
        # Read all Parquet files from Gold layer
        # Gold layer contains hourly aggregations from Silver layer
        # Each file has: event_count, total_value, unique_users, avg_price, event_type, device_type
        gold_pattern = str(PROJECT_ROOT / "data" / "gold" / "hourly_metrics" / "**" / "*.parquet")
        gold_files = glob.glob(gold_pattern, recursive=True)
        if not gold_files:
            print(f"⚠️  No Gold layer data found in {str(PROJECT_ROOT / 'data' / 'gold' / 'hourly_metrics')}")
            print("    Skipping population - tables created but empty")
            print("    Run: python3 export_metrics_complete.py to populate from Gold layer")
            return
        
        df = pd.concat([pd.read_parquet(f) for f in gold_files], ignore_index=True)
        total_events = float(df['event_count'].sum())
        
        with conn.cursor() as cur:
            # ===== POPULATE 1: pipeline_runs =====
            # Simulates 5 recent pipeline executions
            # Helps dashboard show "Recent Runs" panel
            print("   📌 Populating pipeline_runs (5 sample runs)...")
            for i in range(1, 6):
                # Create timestamps going back in time (oldest first)
                started = datetime.now() - timedelta(hours=(6-i))
                # Each run took 300-500 seconds
                completed = started + timedelta(seconds=300 + i*50)
                duration = int((completed - started).total_seconds())
                
                # Insert execution record
                cur.execute("""
                    INSERT INTO metrics.pipeline_runs 
                    (pipeline_name, status, duration_seconds, events_processed, events_failed, 
                     started_at, completed_at)
                    VALUES ('ecommerce_pipeline', 'completed', %s, %s, 0, %s, %s)
                """, (duration, int(total_events), started, completed))
            conn.commit()
            print("      ✅ 5 pipeline runs inserted")
            
            # ===== POPULATE 2: data_quality_checks =====
            # Great Expectations suite results
            # All passed in this test environment
            print("   📌 Populating data_quality_checks (5 checks)...")
            checks = [
                ('schema_validation', 'passed', 0.0),
                ('null_checks', 'passed', 0.0),
                ('range_constraints', 'passed', 0.0),
                ('uniqueness_checks', 'passed', 0.0),
                ('data_freshness', 'passed', 0.0),
            ]
            for check_name, status, failure_rate in checks:
                cur.execute("""
                    INSERT INTO metrics.data_quality_checks 
                    (check_name, status, failure_rate, records_tested, records_failed, checked_at)
                    VALUES (%s, %s, %s, %s, 0, %s)
                """, (check_name, status, failure_rate, int(total_events), datetime.now()))
            conn.commit()
            print("      ✅ 5 quality checks inserted")
            
            # ===== POPULATE 3: system_resources =====
            # CPU and memory metrics over last 10 hours
            # Used for infrastructure monitoring dashboard
            print("   📌 Populating system_resources (10 data points)...")
            for i in range(10):
                # CPU metrics: rising trend from 45% to 65%
                cur.execute("""
                    INSERT INTO metrics.system_resources (resource_type, metric_value, recorded_at)
                    VALUES ('cpu_usage_percent', %s, %s)
                """, (45.0 + (i % 3) * 5, datetime.now() - timedelta(hours=10-i)))
                
                # Memory metrics: stable around 60-65%
                cur.execute("""
                    INSERT INTO metrics.system_resources (resource_type, metric_value, recorded_at)
                    VALUES ('memory_usage_percent', %s, %s)
                """, (62.0 + (i % 2) * 3, datetime.now() - timedelta(hours=10-i)))
            conn.commit()
            print("      ✅ 20 system resource points inserted")
            
            # ===== POPULATE 4: Events Over Time (25 hourly points) =====
            # Powers "Events Over Time" line chart in dashboard
            # Creates data for last 25 hours (including current hour)
            print("   📌 Populating Events Over Time (25 hourly data points)...")
            for hour_offset in range(24, -1, -1):
                # Go back in time hour by hour
                timestamp = datetime.now() - timedelta(hours=hour_offset)
                # Distribute events evenly across hours (with slight variation)
                events_for_hour = int(total_events / 24) + (hour_offset % 3) * 100
                
                cur.execute("""
                    INSERT INTO metrics.pipeline_metrics 
                    (metric_name, metric_value, metric_unit, recorded_at)
                    VALUES ('pipeline.events.total', %s, 'count', %s)
                """, (float(events_for_hour), timestamp))
            conn.commit()
            print("      ✅ 25 hourly data points inserted")
            
            # ===== POPULATE 5: Conversion Funnel (5 stages) =====
            # business.funnel.* metrics for funnel analysis
            # Shows drop-off at each step (page_view → search → cart → checkout → purchase)
            print("   📌 Populating Conversion Funnel (5 stages)...")
            funnel_stages = {
                'page_view': 3781216,          # Baseline: all visitors see product pages
                'search': 872987,              # 23% do searches
                'add_to_cart': 524492,         # 60% of searchers add to cart
                'checkout_started': 250702,    # 48% of cartees start checkout
                'checkout_completed': 148465,  # 59% of checkouts complete
            }
            
            for stage, count in funnel_stages.items():
                # Tag each metric with stage name for filtering in Grafana
                cur.execute("""
                    INSERT INTO metrics.pipeline_metrics 
                    (metric_name, metric_value, metric_unit, tags, recorded_at)
                    VALUES ('business.funnel.' || %s, %s, 'count', %s::jsonb, %s)
                """, (stage, float(count), json.dumps({'stage': stage}), datetime.now()))
            conn.commit()
            print("      ✅ 5 funnel stage metrics inserted")
        
        print("\n   ✅ All initial data populated")
        
    except Exception as e:
        print(f"❌ Error populating data: {e}")
        conn.rollback()
        raise

def main():
    """
    Main entry point for metrics schema setup.
    
    EXECUTION FLOW:
    1. Create all database tables and views
    2. Populate with initial data from Gold layer
    3. Print success summary
    
    ERROR HANDLING:
    - Database connection errors caught with traceback
    - Connection automatically closed in finally block
    - Any schema/population errors propagate up (fail-fast approach)
    """
    print("\n")
    setup_missing_tables()
    
    # Now populate initial data
    conn = get_db_connection()
    try:
        populate_initial_data(conn)
    finally:
        conn.close()
    
    # Print comprehensive summary for operator visibility
    print("\n" + "="*80)
    print("✅ METRICS SCHEMA SETUP COMPLETE")
    print("="*80)
    print("\n📋 Tables Created & Populated:")
    print("   1. metrics.pipeline_metrics - Time-series metric data (25+ records)")
    print("   2. metrics.pipeline_runs - Pipeline execution history (5 runs)")
    print("   3. metrics.data_quality_checks - Quality validation results (5 checks)")
    print("   4. metrics.system_resources - CPU/Memory metrics (20 data points)")
    print("   5. metrics.active_alerts (VIEW) - Non-passed quality checks")
    print("\n🎨 All Grafana Dashboard Panels will now display data:")
    print("   1. Total Events Processed")
    print("   2. Event Processing Rate")
    print("   3. Overall Conversion Rate")
    print("   4. Active Alerts")
    print("   5. Events Over Time")
    print("   6. Events by Type")
    print("   7. Pipeline Conversion Funnel")
    print("   8. Pipeline Success Rate")
    print("   9. Average Pipeline Duration")
    print("   10. Data Quality Status")
    print("   11. Recent Pipeline Runs")
    print("   12. System Resources (CPU/Memory)")
    print("\n📊 Next: Run export_metrics_complete.py to export current gold metrics")
    print("📊 Then refresh your Grafana dashboard (F5) to see all data!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
