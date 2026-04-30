#!/usr/bin/env python3
"""Check what metrics and tables exist in PostgreSQL"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'dataeng',
    'password': 'dataeng123'
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # List all tables in metrics schema
    print("=" * 80)
    print("TABLES IN METRICS SCHEMA")
    print("=" * 80)
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'metrics' 
        ORDER BY table_name
    """)
    
    tables = cur.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check pipeline_metrics table
    print("\n" + "=" * 80)
    print("PIPELINE_METRICS TABLE")
    print("=" * 80)
    
    cur.execute("SELECT COUNT(*) FROM metrics.pipeline_metrics;")
    count = cur.fetchone()[0]
    print(f"Total records: {count:,}\n")
    
    cur.execute("""
        SELECT DISTINCT metric_name 
        FROM metrics.pipeline_metrics 
        ORDER BY metric_name
    """)
    
    print("Metrics exported:")
    for row in cur.fetchall():
        print(f"  - {row[0]}")
    
    # Check for business metrics specifically
    print("\n" + "=" * 80)
    print("BUSINESS METRICS")
    print("=" * 80)
    
    cur.execute("""
        SELECT metric_name, metric_value, recorded_at
        FROM metrics.pipeline_metrics
        WHERE metric_name LIKE 'business.%'
        ORDER BY metric_name
        LIMIT 20
    """)
    
    business_metrics = cur.fetchall()
    for name, value, timestamp in business_metrics:
        print(f"  {name}: {value:.2f} @ {timestamp}")
    
    if not business_metrics:
        print("  (No business metrics found)")
    
    cur.close()
    conn.close()
    
    print("\n✅ Query complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
