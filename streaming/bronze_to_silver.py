#!/usr/bin/env python3
"""
BRONZE TO SILVER - Data Cleaning & Validation
==============================================

Simplified version that works with Delta Lake streaming.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_date, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming.utils.spark_session import get_spark_session

BRONZE_PATH = os.path.join(os.path.expanduser("~"), "data-engineering-projects", "ecommerce-streaming-platform-uv", "data", "bronze")
SILVER_PATH = os.path.join(os.path.expanduser("~"), "data-engineering-projects", "ecommerce-streaming-platform-uv", "data", "silver")

# Define schema for parsing JSON
clickstream_schema = StructType([
    StructField("event_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("session_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("category", StringType(), True),
    StructField("device_type", StringType(), True),
    StructField("country", StringType(), True),
    StructField("timestamp", StringType(), True),
])

def process_silver_batch(spark):
    """Process Bronze to Silver using BATCH mode (simpler, more reliable)"""
    
    print("Reading Bronze Parquet table...")
    
    # Read Bronze as BATCH (not stream)
    bronze_df = spark.read.format("parquet").load(f"{BRONZE_PATH}/clickstream")
    
    print(f"✓ Bronze records: {bronze_df.count():,}")
    
    # Parse JSON and transform
    silver_df = (bronze_df
        .withColumn("data", from_json(col("value").cast("string"), clickstream_schema))
        .select("data.*", "ingestion_timestamp", "kafka_offset")
        .withColumn("event_date", to_date(col("timestamp")))
        .withColumn("processed_at", current_timestamp())
    )
    
    print("Writing to Silver Parquet table...")
    
    # Write to Silver (batch mode)
    (silver_df
        .write
        .format("parquet")
        .mode("append")  # Append new data
        .partitionBy("event_date")
        .save(f"{SILVER_PATH}/clickstream")
    )
    
    print(f"✓ Silver records written: {silver_df.count():,}")

def main():
    print("="*80)
    print("BRONZE → SILVER - Batch Processing")
    print("="*80)
    print()
    
    spark = get_spark_session("BronzeToSilver")
    
    try:
        process_silver_batch(spark)
        print("\n✅ SUCCESS! Silver layer created")
        print(f"Location: {SILVER_PATH}/clickstream")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()