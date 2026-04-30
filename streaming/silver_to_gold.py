#!/usr/bin/env python3
"""
SILVER TO GOLD - Business Aggregations (BATCH)
===============================================

Creates business-level aggregates for analytics.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as _sum, avg, hour
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming.utils.spark_session import get_spark_session


BRONZE_PATH = os.path.join(os.path.expanduser("~"), "data-engineering-projects", "ecommerce-streaming-platform-uv", "data", "bronze")
SILVER_PATH = os.path.join(os.path.expanduser("~"), "data-engineering-projects", "ecommerce-streaming-platform-uv", "data", "silver")
GOLD_PATH = os.path.join(os.path.expanduser("~"), "data-engineering-projects", "ecommerce-streaming-platform-uv", "data", "gold")
def create_hourly_metrics(spark):
    """Aggregate events by hour"""
    
    print("Reading Silver Parquet table...")
    silver_df = spark.read.format("parquet").load(f"{SILVER_PATH}/clickstream")
    
    print(f"✓ Silver records: {silver_df.count():,}")
    
    # Add hour column and aggregate
    hourly_metrics = (silver_df
        .withColumn("event_hour", hour(col("timestamp")))
        .groupBy("event_date", "event_hour", "event_type", "device_type")
        .agg(
            count("*").alias("event_count"),
            count("user_id").alias("unique_users"),
            avg("price").alias("avg_price"),
            _sum("price").alias("total_value")
        )
    )
    
    print("Writing to Gold Parquet table...")
    
    (hourly_metrics
        .write
        .format("parquet")
        .mode("append")
        .save(f"{GOLD_PATH}/hourly_metrics")
    )
    
    print(f"✓ Gold metrics written: {hourly_metrics.count():,}")

def main():
    print("="*80)
    print("SILVER → GOLD - Business Aggregations")
    print("="*80)
    print()
    
    spark = get_spark_session("SilverToGold")
    
    try:
        create_hourly_metrics(spark)
        print("\n✅ SUCCESS! Gold layer created")
        print(f"Location: {GOLD_PATH}/hourly_metrics")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()