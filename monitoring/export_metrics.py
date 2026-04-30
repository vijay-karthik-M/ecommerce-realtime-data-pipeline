#!/usr/bin/env python3
"""
DAY 7: MONITORING & METRICS
===========================

Export metrics to PostgreSQL for Grafana dashboards
"""

import psycopg2
from datetime import datetime
from pyspark.sql import SparkSession
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming.utils.spark_session import get_spark_session

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'dataeng',
    'password': 'dataeng123'
}

def export_pipeline_metrics(spark):
    """Export pipeline metrics"""
    
    # Define full path to silver layer
    SILVER_PATH = os.path.join(os.path.expanduser("~"), "data-engineering-projects", "ecommerce-streaming-platform-uv", "data", "silver")
    
    # Get Silver metrics (Parquet format)
    silver_df = spark.read.format("parquet").load(f"{SILVER_PATH}/clickstream")
    
    total_events = silver_df.count()
    events_by_type = silver_df.groupBy("event_type").count().collect()
    events_by_device = silver_df.groupBy("device_type").count().collect()
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Insert metrics
    for row in events_by_type:
        cur.execute("""
            INSERT INTO metrics.pipeline_metrics (metric_name, metric_value, recorded_at)
            VALUES (%s, %s, %s)
        """, (f"events_{row['event_type']}", row['count'], datetime.now()))
    
    for row in events_by_device:
        cur.execute("""
            INSERT INTO metrics.pipeline_metrics (metric_name, metric_value, recorded_at)
            VALUES (%s, %s, %s)
        """, (f"device_{row['device_type']}", row['count'], datetime.now()))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Exported {total_events:,} events to metrics")

def create_metrics_tables():
    """Create metrics tables in PostgreSQL"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS metrics;
        
        CREATE TABLE IF NOT EXISTS metrics.pipeline_metrics (
            id SERIAL PRIMARY KEY,
            metric_name VARCHAR(100),
            metric_value NUMERIC,
            recorded_at TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics.pipeline_metrics(recorded_at);
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Metrics tables created")

def main():
    print("="*80)
    print("DAY 7: EXPORTING METRICS FOR GRAFANA")
    print("="*80)
    
    spark = get_spark_session("MetricsExport")
    
    try:
        create_metrics_tables()
        export_pipeline_metrics(spark)
        
        print("\n✅ Metrics ready for Grafana!")
        print("   Access Grafana at: http://localhost:3000")
        print("   Username: admin, Password: admin123")
        
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
