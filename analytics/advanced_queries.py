#!/usr/bin/env python3
"""
DAY 6: ADVANCED ANALYTICS & OPTIMIZATION
=========================================

Complex queries, window functions, Delta Lake optimization
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from delta.tables import DeltaTable
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming.utils.spark_session import get_spark_session

def funnel_analysis(spark):
    """Conversion funnel with window functions"""
    print("\n📊 FUNNEL ANALYSIS")
    print("="*80)
    
    df = spark.read.format("delta").load("../data/silver/clickstream")
    
    # Create funnel stages
    funnel = df.groupBy("session_id").agg(
        max(when(col("event_type") == "page_view", 1).otherwise(0)).alias("viewed"),
        max(when(col("event_type") == "search", 1).otherwise(0)).alias("searched"),
        max(when(col("event_type") == "add_to_cart", 1).otherwise(0)).alias("added_cart"),
        max(when(col("event_type") == "checkout_started", 1).otherwise(0)).alias("started_checkout"),
        max(when(col("event_type") == "checkout_completed", 1).otherwise(0)).alias("purchased")
    )
    
    # Calculate conversion rates
    conversions = funnel.agg(
        (sum("searched") / sum("viewed") * 100).alias("view_to_search_pct"),
        (sum("added_cart") / sum("searched") * 100).alias("search_to_cart_pct"),
        (sum("started_checkout") / sum("added_cart") * 100).alias("cart_to_checkout_pct"),
        (sum("purchased") / sum("started_checkout") * 100).alias("checkout_to_purchase_pct")
    )
    
    conversions.show()
    return conversions

def cohort_analysis(spark):
    """User cohort analysis with window functions"""
    print("\n👥 COHORT ANALYSIS")
    print("="*80)
    
    df = spark.read.format("delta").load("../data/silver/clickstream")
    
    # First purchase date per user
    window_spec = Window.partitionBy("user_id").orderBy("timestamp")
    
    cohorts = df.withColumn("user_first_event", first("timestamp").over(window_spec)) \
        .withColumn("cohort_month", date_trunc("month", "user_first_event")) \
        .withColumn("event_month", date_trunc("month", "timestamp"))
    
    # Retention by cohort
    retention = cohorts.groupBy("cohort_month", "event_month").agg(
        countDistinct("user_id").alias("users")
    ).orderBy("cohort_month", "event_month")
    
    retention.show(20)
    return retention

def rfm_analysis(spark):
    """RFM (Recency, Frequency, Monetary) segmentation"""
    print("\n💰 RFM ANALYSIS")
    print("="*80)
    
    df = spark.read.format("delta").load("../data/silver/clickstream")
    purchases = df.filter(col("event_type") == "checkout_completed")
    
    # Calculate RFM
    rfm = purchases.groupBy("user_id").agg(
        datediff(current_date(), max("timestamp")).alias("recency"),
        count("*").alias("frequency"),
        sum("price").alias("monetary")
    )
    
    # Create quartiles
    rfm_quartiles = rfm.withColumn(
        "r_quartile", ntile(4).over(Window.orderBy(desc("recency")))
    ).withColumn(
        "f_quartile", ntile(4).over(Window.orderBy("frequency"))
    ).withColumn(
        "m_quartile", ntile(4).over(Window.orderBy("monetary"))
    ).withColumn(
        "rfm_score", concat(col("r_quartile"), col("f_quartile"), col("m_quartile"))
    )
    
    rfm_quartiles.show(20)
    return rfm_quartiles

def optimize_delta_tables(spark):
    """Delta Lake optimization"""
    print("\n⚡ DELTA LAKE OPTIMIZATION")
    print("="*80)
    
    # OPTIMIZE with Z-ORDER
    silver_table = DeltaTable.forPath(spark, "../data/silver/clickstream")
    
    print("Running OPTIMIZE...")
    silver_table.optimize().executeCompaction()
    
    print("Running Z-ORDER on event_type (non-partition columns only)...")
    silver_table.optimize().executeZOrderBy("event_type")
    
    # VACUUM (remove old files)
    print("Running VACUUM (dry run)...")
    silver_table.vacuum(retentionHours=168)  # 7 days
    
    print("✅ Optimization complete")

def advanced_sql_queries(spark):
    """Complex SQL with CTEs and window functions"""
    print("\n🔍 ADVANCED SQL QUERIES")
    print("="*80)
    
    df = spark.read.format("delta").load("../data/silver/clickstream")
    df.createOrReplaceTempView("events")
    
    # Query 1: Daily active users with 7-day rolling average
    query1 = spark.sql("""
        WITH daily_users AS (
            SELECT 
                DATE(timestamp) as date,
                COUNT(DISTINCT user_id) as dau
            FROM events
            GROUP BY DATE(timestamp)
        )
        SELECT 
            date,
            dau,
            AVG(dau) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as dau_7day_avg
        FROM daily_users
        ORDER BY date DESC
        LIMIT 30
    """)
    
    print("\n📅 Daily Active Users (7-day rolling avg):")
    query1.show()
    
    # Query 2: User journey paths
    query2 = spark.sql("""
        SELECT 
            user_id,
            COLLECT_LIST(event_type) as journey_path,
            COUNT(*) as steps
        FROM (
            SELECT 
                user_id,
                event_type,
                ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp) as step_num
            FROM events
        )
        WHERE step_num <= 5
        GROUP BY user_id
        HAVING steps >= 3
        LIMIT 10
    """)
    
    print("\n🛤️  User Journey Paths:")
    query2.show(truncate=False)
    
    return query1, query2

def main():
    """Main execution"""
    print("="*80)
    print("DAY 6: ADVANCED ANALYTICS & OPTIMIZATION")
    print("="*80)
    
    spark = get_spark_session("AdvancedAnalytics")
    
    try:
        # Run analytics
        funnel_analysis(spark)
        cohort_analysis(spark)
        rfm_analysis(spark)
        advanced_sql_queries(spark)
        
        # Optimize
        optimize_delta_tables(spark)
        
        print("\n✅ All analytics complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
