#!/usr/bin/env python3
"""Run the metrics schema creation script"""

import psycopg2
import sys

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'dataeng',
    'password': 'dataeng123'
}

try:
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Reading SQL schema file...")
    with open('create_metrics_schema.sql', 'r') as f:
        sql_script = f.read()
    
    print("Executing SQL schema creation...")
    cur.execute(sql_script)
    conn.commit()
    
    print("\n✅ Metrics schema created successfully!\n")
    
    # Check what was created
    print("=" * 80)
    print("TABLES CREATED")
    print("=" * 80)
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'metrics' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    
    tables = cur.fetchall()
    for table in tables:
        print(f"  ✓ {table[0]}")
    
    print("\n" + "=" * 80)
    print("VIEWS CREATED")
    print("=" * 80)
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'metrics' 
        AND table_type = 'VIEW'
        ORDER BY table_name
    """)
    
    views = cur.fetchall()
    if views:
        for view in views:
            print(f"  ✓ {view[0]}")
    else:
        print("  (No views found)")
    
    # Test the views
    print("\n" + "=" * 80)
    print("TESTING VIEWS")
    print("=" * 80)
    
    try:
        cur.execute("SELECT COUNT(*) FROM metrics.latest_metrics;")
        count = cur.fetchone()[0]
        print(f"✅ metrics.latest_metrics: {count} rows")
    except Exception as e:
        print(f"❌ metrics.latest_metrics: {e}")
    
    try:
        cur.execute("SELECT * FROM metrics.pipeline_health LIMIT 1;")
        result = cur.fetchone()
        print(f"✅ metrics.pipeline_health: View exists and works")
    except Exception as e:
        print(f"❌ metrics.pipeline_health: {e}")
    
    cur.close()
    conn.close()
    
    print("\n✅ All done!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
