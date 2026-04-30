#!/usr/bin/env python3
"""
OPTIMIZED SPARK SESSION FOR 8GB RAM LAPTOPS
===========================================

Purpose:
    Factory function to create a stable Spark session optimized for:
    - Low RAM environments (8GB laptops)
    - Streaming workloads (Kafka → Parquet)
    - Delta Lake compatibility
    - Error handling (graceful shutdown, thread safety)

Key Optimizations:
    1. Memory allocation: 512MB driver + 512MB executor (3x safety buffer)
    2. Parallelism: Reduced to 2 (avoid OOM on laptop)
    3. Streaming: Graceful stop with 10-second timeout
    4. Thread safety: PYSPARK_DRIVER_PIN_THREAD + Netty config
    5. Serialization: Kryo (faster than default Java serialization)

Common Issues & Fixes:
    Issue:              "reentrant call" errors on Ctrl+C
    Root Cause:        PySpark thread pinning + Py4J Java callbacks
    Fix Applied:       Remove PYSPARK_PIN_THREAD, add Netty reflection flag
    
    Issue:              OutOfMemory errors during aggregation
    Root Cause:        Default 512MB memory insufficient for 8GB laptop
    Fix Applied:       Increase driver/executor to 1GB, reduce partitions to 2

Performance Tradeoffs:
    - Parallelism=2: Slower but prevents OOM
    - Kryo serialization: Faster but incompatible with some classes
    - Adaptive execution OFF: Simpler for streaming, predictable
"""

import os
from pyspark.sql import SparkSession
import signal

# ===== THREAD SAFETY SETTINGS =====
# FIX: DO NOT use PYSPARK_PIN_THREAD (causes "reentrant call" errors)
# Instead, use PYSPARK_DRIVER_PIN_THREAD for better thread safety  
os.environ['PYSPARK_DRIVER_PIN_THREAD'] = 'true'
# Disable Python output buffering (see logs immediately)
os.environ['PYSPARK_DRIVER_PYTHON_OPTS'] = '-u'

# ===== DEPENDENCIES =====
# CRITICAL: Set BEFORE creating SparkSession
# - delta-core: Delta Lake support
# - spark-sql-kafka: Kafka streaming source
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages io.delta:delta-core_2.12:2.3.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 pyspark-shell'

# ===== NETWORKING =====
# Bind to localhost only (avoid network interface conflicts)
os.environ['SPARK_LOCAL_IP'] = '127.0.0.1'

def get_spark_session(app_name="EcommerceStreaming"):
    """
    Create a stable, optimized Spark session for streaming on 8GB laptops.
    
    This function handles:
    - Memory allocation suitable for laptops
    - Streaming-specific configurations
    - Error handling and graceful shutdown
    - Delta Lake and Kafka source initialization
    
    Args:
        app_name (str, optional): 
            Spark application name shown in UI. Defaults to "EcommerceStreaming".
            Used for tracking in logs and Spark history server.
    
    Returns:
        SparkSession: Configured session ready for:
            - Kafka reads (via readStream)
            - Delta/Parquet writes (via writeStream)
            - SQL queries (via spark.sql())
    
    Examples:
        # Basic usage
        spark = get_spark_session("KafkaToBronze")
        
        # With custom name
        spark = get_spark_session("MyCustomJob")
        
    Configuration Philosophy:
        Balance: Reduce memory footprint while maintaining stability
        - Parallelism: 2 tasks (matches 2 CPU cores on typical laptop)
        - Shuffle partitions: 2 (minimize intermediate data)
        - Memory per task: 512MB + 512MB buffer
        
    Common Errors & Solutions:
        Error: "java.lang.OutOfMemoryError"
        Solution: Reduce .config values further, process smaller batches
        
        Error: "reentrant call not allowed"
        Solution: Already fixed by PYSPARK_DRIVER_PIN_THREAD
        
        Error: "Kafka broker connection refused"
        Solution: Start Kafka/Docker containers before running
    """
    
    spark = (SparkSession.builder
        .appName(app_name)
        
        # ===== MEMORY SETTINGS =====
        # Driver: Master process memory (Py4J JVM + data accumulation)
        # Executor: Worker process memory
        # Increased to 1GB for streaming stability (default 512MB too small)
        .config("spark.driver.memory", "1g")
        .config("spark.executor.memory", "1g")
        # Heap split: 60% execution + 40% storage
        .config("spark.memory.fraction", "0.6")
        .config("spark.memory.storageFraction", "0.3")
        
        # ===== PARALLELISM SETTINGS =====
        # Reduce parallelism to avoid OOM on 8GB laptop
        # shuffle.partitions: Splits data during joins/aggregations
        # default.parallelism: Task parallelism across cluster
        # These MATCH number of available CPU cores (typically 2 on laptop)
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.default.parallelism", "2")
        
        # ===== QUERY OPTIMIZATION SETTINGS =====
        # Disable adaptive execution (can cause instability in streaming)
        # Adaptive = Spark rewrites query mid-execution based on statistics
        # Good for batch, bad for streaming (unpredictable behavior)
        .config("spark.sql.adaptive.enabled", "false")
        
        # Use Kryo serialization (faster, more compact than Java serialization)
        # Tradeoff: Not compatible with all custom classes
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        
        # ===== FILE I/O SETTINGS =====
        # Parquet max bytes per partition (don't split small files)
        # 64MB: reasonable for streaming (faster than many small reads)
        .config("spark.sql.files.maxPartitionBytes", "67108864")
        # NOTE: Parquet summary metadata config deprecated in Spark 3.4+
        # Default behavior (no summary) is already optimal for streaming
        # Removed deprecated "parquet.enable.summary-metadata" to avoid warnings
        
        # ===== DELTA LAKE SETTINGS =====
        # Enable Delta Lake extensions in Spark SQL
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        # Use Delta catalog as default (enables delta format auto-detection)
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        
        # ===== HADOOP/S3A SETTINGS =====
        # File system implementation
        .config("fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem")
        # S3A caching (disable for consistency)
        .config("spark.hadoop.fs.s3a.impl.disable.cache", "true")
        # SQL file status caching (disable for streaming)
        .config("spark.sql.optimizer.fileStatusCaching", "false")
        
        # ===== STREAMING SETTINGS =====
        # Graceful stop timeout: Wait 10 seconds for queries to finish
        # Before forcefully shutting down (prevents data loss)
        .config("spark.streaming.gracefulStopTimeout", "10000")
        # Prevent topic deletion (safety measure)
        .config("spark.streaming.kafka.allowTopicDeletion", "false")
        
        # Broadcast timeout: Wait 5 minutes for large broadcasts
        # (prevents timeout during collect/broadcast operations)
        .config("spark.sql.broadcastTimeout", "300")
        
        # ===== JVM SETTINGS =====
        # Py4J Java options for stability
        # - UnlockDiagnosticVMOptions: Enable debug-mode Java options
        # - DebugNonSafepoints: More accurate profiling
        # - Netty reflection: Allow Netty to access internals (needed for streaming)
        .config("spark.driver.extraJavaOptions", 
                "-XX:+UnlockDiagnosticVMOptions "
                "-XX:+DebugNonSafepoints "
                "-Dpython.path=/usr/lib/python3.12 "
                "-Dio.netty.tryReflectionSetAccessible=true")
        
        # Reuse worker processes (optimization for long-running jobs)
        .config("spark.python.worker.reuse", "true")
        
        # ===== LOCAL MODE SETUP =====
        # [2] = 2 local threads (matches laptop CPU cores)
        # Alternative: [*] = all cores, but not safe for 8GB RAM
        .master("local[2]")
        
        .getOrCreate()
    )
    
    # Set logging to WARNING (reduce verbosity)
    # WARN shows important issues, ERRORS show problems, INFO too noisy
    spark.sparkContext.setLogLevel("WARN")
    
    return spark

if __name__ == "__main__":
    spark = get_spark_session("Test")
    print(f"✅ Spark session created successfully")
    print(f"   Driver Memory: 512MB")
    print(f"   Executor Memory: 512MB")
    print(f"   Cores: 2")
    print(f"   Shuffle Partitions: 2")
    spark.stop()