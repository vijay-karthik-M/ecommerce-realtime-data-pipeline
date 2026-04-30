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

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp, date_format
from pyspark.sql.types import StructType, StructField, StringType, TimestampType
from pyspark.sql.streaming import StreamingQueryListener
import sys
import os
import time
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streaming.utils.spark_session import get_spark_session


# KAFKA CONFIGURATION
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPICS = {
    'clickstream': 'ecommerce.clickstream.v1',
    'transactions': 'ecommerce.transactions.v1'
}

# DELTA LAKE PATHS
BRONZE_PATH = os.path.join(os.path.expanduser("~"), "data-engineering-projects", "ecommerce-streaming-platform-uv", "data", "bronze")


class ProgressListener(StreamingQueryListener):
    """
    Monitor Spark Structured Streaming query progress and output metrics.
    
    This listener is called automatically by Spark after each micro-batch completes.
    It tracks:
    - Number of rows processed per batch
    - Processing duration
    - Query status and any errors
    
    Why custom listener?
    - Provides real-time visibility into stream health
    - Enables alerting on stalls or failures
    - Captures per-batch performance metrics
    """
    
    def onQueryStarted(self, event):
        try:
            query_id = event.runId
            print(f"  ✓ Query started: {query_id}")
        except:
            pass  # Suppress errors if event structure differs
    
    def onQueryProgress(self, event):
        """Print progress metrics on each batch."""
        try:
            progress = event.progress
            if progress.numInputRows > 0:
                print(f"  📊 Rows={progress.numInputRows} | "
                      f"Batch={progress.batchId} | "
                      f"Duration={progress.durationMs.get('processingTime', 0)}ms")
        except:
            pass  # Suppress errors during progress tracking
    
    def onQueryIdle(self, event):
        """Called when query is idle (waiting for data)."""
        pass  # Suppress idle messages for cleaner output
    
    def onQueryTerminated(self, event):
        try:
            query_id = event.runId
            print(f"  ✓ Query terminated: {query_id}")
        except:
            print(f"  ✓ Query terminated gracefully")  # Fallback message


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
    """
    
    # Use "earliest" only on first run (when checkpoint doesn't exist)
    # On restart, checkpoint position overrides startingOffsets
    offset_mode = "earliest" if use_earliest else "latest"
    
    df = (spark
        .readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPICS[topic])
        .option("startingOffsets", offset_mode)
        
        # Rate limiting per micro-batch
        .option("maxOffsetsPerTrigger", 5000)
        
        # Kafka connection options
        .option("kafka.connections.max.idle.ms", "540000")
        .option("kafka.session.timeout.ms", "30000")
        
        # Don't fail if Kafka deletes old data
        .option("failOnDataLoss", "false")
        
        .load()
    )
    
    print(f"✓ Connected to Kafka topic: {KAFKA_TOPICS[topic]}")
    return df


def write_to_bronze(df, topic: str, checkpoint_location: str):
    """
    Write streaming data to Bronze Delta table.
    
    CONCEPT: Bronze Layer
    - Minimal transformation (just add metadata)
    - Raw JSON preserved (as-is from Kafka)
    - Partitioned by date for efficient queries
    """
    
    # Add ingestion metadata (no JSON parsing - preserve raw data)
    bronze_df = (df
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("source_topic", col("topic"))
        .withColumn("kafka_partition", col("partition"))
        .withColumn("kafka_offset", col("offset"))
        .withColumn("kafka_timestamp", col("timestamp"))
        .withColumn("ingestion_date", date_format(current_timestamp(), "yyyy-MM-dd"))
    )
    
    query = (bronze_df
        .writeStream
        .format("parquet")
        .outputMode("append")
        
        .option("checkpointLocation", checkpoint_location)
        .option("path", f"{BRONZE_PATH}/{topic}")
        .partitionBy("ingestion_date")
        
        # [8GB OPTIMIZATION] Increased trigger for laptop processing time
        # Original: 5 seconds caused batch lag (processing took 7.5s)
        # Recommended: 10-15 seconds for reliable processing on limited hardware
        # Trade-off: 10s latency vs. reliable/no backlog
        .trigger(processingTime="10 seconds")
        
        # Add query name for tracking
        .queryName(f"Bronze_{topic}")
        
        .start()
    )
    
    print(f"✓ Streaming to Bronze: {BRONZE_PATH}/{topic}")
    print(f"  Checkpoint: {checkpoint_location}")
    print(f"  Trigger interval: 10 seconds (optimized for 8GB systems)")
    
    return query


def main():
    """Main execution"""
    print("=" * 80)
    print("KAFKA TO BRONZE - Real-time Ingestion")
    print("=" * 80)
    print()
    
    spark = None
    clickstream_query = None
    transaction_query = None
    
    try:
        # Initialize Spark
        spark = get_spark_session("KafkaToBronze")
        
        # Add progress listener to monitor streaming
        spark.streams.addListener(ProgressListener())
        
        # Check if checkpoint exists (determines if we read from beginning or resume)
        clicks_checkpoint = f"{BRONZE_PATH}/_checkpoints/clickstream"
        trans_checkpoint = f"{BRONZE_PATH}/_checkpoints/transactions"
        
        use_earliest_clicks = not Path(clicks_checkpoint).exists()
        use_earliest_trans = not Path(trans_checkpoint).exists()
        
        print(f"\n📍 CHECKPOINT STATUS:")
        print(f"  Clickstream: {'CREATE NEW (starting from earliest)' if use_earliest_clicks else 'RESUME (using checkpoint)'}")
        print(f"  Transactions: {'CREATE NEW (starting from earliest)' if use_earliest_trans else 'RESUME (using checkpoint)'}")
        print()
        
        # Process clickstream
        print("--- Clickstream Pipeline ---")
        clickstream_df = read_from_kafka(spark, 'clickstream', use_earliest=use_earliest_clicks)
        clickstream_query = write_to_bronze(
            clickstream_df,
            'clickstream',
            clicks_checkpoint
        )
        
        # Process transactions
        print("\n--- Transaction Pipeline ---")
        transaction_df = read_from_kafka(spark, 'transactions', use_earliest=use_earliest_trans)
        transaction_query = write_to_bronze(
            transaction_df,
            'transactions',
            trans_checkpoint
        )
        
        print("\n" + "=" * 80)
        print("🚀 STREAMING STARTED - Processing data from Kafka")
        print("=" * 80)
        print("\n📊 Progress will appear below as data flows:")
        print("(Press Ctrl+C to stop gracefully)\n")
        
        # Keep running until interrupted
        clickstream_query.awaitTermination()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping streams gracefully...")
        _cleanup_streams(spark, clickstream_query, transaction_query)
        print("✓ Stopped gracefully")
        
    except Exception as e:
        print(f"\n❌ STREAMING ERROR: {type(e).__name__}")
        error_msg = str(e)[:500]
        print(f"   Details: {error_msg}")
        print("\n🛑 Attempting graceful shutdown...")
        _cleanup_streams(spark, clickstream_query, transaction_query)
        sys.exit(1)


def _cleanup_streams(spark, clickstream_query, transaction_query):
    """
    Safely cleanup Spark session and queries.
    Suppresses errors during signal handling (Ctrl+C).
    """
    print("\n  Stopping queries...")
    
    # Stop clickstream
    if clickstream_query is not None:
        try:
            if clickstream_query.isActive:
                clickstream_query.stop()
                print("  ✓ Clickstream stopped")
        except Exception as e:
            # Suppress errors during stop
            pass
    
    # Stop transaction
    if transaction_query is not None:
        try:
            if transaction_query.isActive:
                transaction_query.stop()
                print("  ✓ Transactions stopped")
        except Exception as e:
            # Suppress errors during stop
            pass
    
    # Stop Spark session
    if spark is not None:
        try:
            spark.stop()
            print("  ✓ Spark stopped")
        except Exception as e:
            # Suppress errors during stop
            pass
    
    print("✓ Shutdown complete")


if __name__ == "__main__":
    main()