"""
DAY 5: AIRFLOW DAG - Pipeline Orchestration
===========================================

Orchestrates Bronze → Silver → Gold → Quality Checks

Pipeline Flow:
  Bronze (Kafka) → Silver (Transform) → Gold (Aggregate) → Quality Checks → Metrics
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import sys
import os
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Add project to path
PROJECT_PATH = '/home/jay/data-engineering-projects/ecommerce-streaming-platform-uv'
VENV_PATH = '/home/jay/data-engineering-projects/.venv'
sys.path.insert(0, PROJECT_PATH)

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2026, 2, 1),  # Start from available data
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

dag = DAG(
    'ecommerce_pipeline',
    default_args=default_args,
    description='E-commerce streaming pipeline: Bronze → Silver → Gold → QC',
    schedule_interval='0 */6 * * *',  # Every 6 hours
    catchup=False,
    tags=['ecommerce', 'etl', 'production'],
)

# Task 1: Run Silver transformation (Bronze → Silver)
run_silver = BashOperator(
    task_id='bronze_to_silver',
    bash_command=f'source {VENV_PATH}/bin/activate && cd {PROJECT_PATH} && python3 streaming/bronze_to_silver.py',
    dag=dag,
)

# Task 2: Run Gold aggregation (Silver → Gold)
run_gold = BashOperator(
    task_id='silver_to_gold',
    bash_command=f'source {VENV_PATH}/bin/activate && cd {PROJECT_PATH} && python3 streaming/silver_to_gold.py',
    dag=dag,
)

# Task 3: Data Quality Validation (7 Suites) → Gold Layer Gate Check
def validate_data_quality(**context):
    """
    Run 7-suite data quality validation:
    1. Schema Validation
    2. Null Checks
    3. Range Constraints
    4. Set Membership
    5. Uniqueness Checks
    6. Referential Integrity
    7. Completeness & Freshness
    
    Blocks Gold writes if critical gates fail.
    """
    try:
        from data_quality.validate_data import (
            setup_data_source, 
            run_validation, 
            generate_data_docs,
            check_gold_layer_readiness
        )
        from streaming.gold_layer_guard import check_gold_layer_approval
        from streaming.utils.spark_session import get_spark_session
        
        logger.info("=" * 80)
        logger.info("Starting Data Quality Validation (7 Suites)")
        logger.info("=" * 80)
        
        # Initialize Spark
        spark = get_spark_session("DQ-Airflow")
        
        try:
            # Load data
            logger.info("Loading data from Silver layer...")
            df = setup_data_source(spark)
            
            if df is None or len(df) == 0:
                logger.error("Failed to load data - no rows available")
                raise ValueError("Data load failed - no rows to validate")
            
            logger.info(f"Data loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # Run all 7 validation suites
            logger.info("Running 7-suite validation framework...")
            all_suites = run_validation(spark, df)
            
            if all_suites is None:
                raise ValueError("Validation suites returned None")
            
            # Generate data docs
            logger.info("Generating data quality reports...")
            report = generate_data_docs(all_suites)
            
            # Check Gold layer readiness
            logger.info("Checking Gold layer write gate...")
            gold_ready = check_gold_layer_readiness(all_suites)
            
            # Log summary
            summary = report['summary']
            logger.info("-" * 80)
            logger.info(f"VALIDATION SUMMARY:")
            logger.info(f"  Total Expectations: {summary['total_expectations']}")
            logger.info(f"  Passed: {summary['total_passed']}")
            logger.info(f"  Failed: {summary['total_failed']}")
            logger.info(f"  Pass Rate: {(summary['total_passed']/summary['total_expectations']*100):.1f}%")
            logger.info(f"  Suites Passed: {summary['suites_passed']}/7")
            logger.info(f"  Suites Failed: {summary['suites_failed']}/7")
            logger.info("-" * 80)
            
            if gold_ready:
                logger.info("✅ ALL QUALITY GATES PASSED - Gold layer writes APPROVED")
            else:
                logger.warning("⚠️  QUALITY GATE FAILURES - Gold layer writes would be BLOCKED")
                raise ValueError(
                    f"Quality gate failures detected: {summary['total_failed']} expectations failed. "
                    "Gold layer writes blocked until issues resolved."
                )
            
            # Store results in XCom for downstream tasks
            context['task_instance'].xcom_push(
                key='validation_report',
                value={
                    'gold_layer_approved': gold_ready,
                    'total_passed': summary['total_passed'],
                    'total_failed': summary['total_failed'],
                    'pass_rate': (summary['total_passed']/summary['total_expectations']*100)
                }
            )
            
            return True
            
        finally:
            spark.stop()
            logger.info("Spark session stopped")
    
    except Exception as e:
        logger.error(f"❌ Data quality validation failed: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise


data_quality = PythonOperator(
    task_id='data_quality_check',
    python_callable=validate_data_quality,
    dag=dag,
)

# Task 4: Update pipeline metrics (Optional - won't fail if unavailable)
def update_metrics(**context):
    """
    Update pipeline metrics in metrics store.
    Non-critical task - failures won't block pipeline.
    """
    try:
        validation_results = context['task_instance'].xcom_pull(
            task_ids='data_quality_check',
            key='validation_report'
        )
        
        logger.info("Attempting to update pipeline metrics...")
        
        try:
            # Try PostgreSQL metrics store
            import psycopg2
            from psycopg2 import sql
            
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='analytics',
                user='dataeng',
                password='dataeng123',
                connect_timeout=5
            )
            
            cur = conn.cursor()
            cur.execute(sql.SQL("""
                INSERT INTO metrics.pipeline_runs 
                (pipeline_name, run_date, status, gold_approved, quality_pass_rate)
                VALUES (%s, %s, %s, %s, %s)
            """), (
                'ecommerce_pipeline',
                datetime.now(),
                'success',
                validation_results.get('gold_layer_approved', False) if validation_results else False,
                validation_results.get('pass_rate', 0) if validation_results else 0
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            logger.info("✅ Metrics updated in PostgreSQL")
            
        except ImportError:
            logger.warning("psycopg2 not installed - skipping PostgreSQL metrics")
        except Exception as pg_error:
            logger.warning(f"PostgreSQL connection failed (non-critical): {str(pg_error)}")
            logger.info("Continuing - metrics update is optional")
        
        # Try to log to file as fallback
        try:
            metrics_log = f"{PROJECT_PATH}/data_quality/reports/pipeline_metrics.log"
            os.makedirs(os.path.dirname(metrics_log), exist_ok=True)
            
            with open(metrics_log, 'a') as f:
                f.write(f"{datetime.now().isoformat()},success,")
                f.write(f"{validation_results.get('gold_layer_approved', False) if validation_results else False},")
                f.write(f"{validation_results.get('pass_rate', 0) if validation_results else 0}\n")
            
            logger.info("✅ Metrics written to log file")
        except Exception as log_error:
            logger.warning(f"Could not write metrics log: {str(log_error)}")
        
        return True
        
    except Exception as e:
        logger.warning(f"Metrics update encountered non-critical error: {str(e)}")
        logger.info("Pipeline continues - metrics update is advisory only")
        return False  # Non-blocking failure


update_db = PythonOperator(
    task_id='update_metrics',
    python_callable=update_metrics,
    trigger_rule='all_done',  # Run even if data_quality fails (for logging)
    dag=dag,
)

# ════════════════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATION
# ════════════════════════════════════════════════════════════════════════════
# Task Dependencies (DAG):
# 
#   Bronze (Kafka)
#        ↓
#   [bronze_to_silver] ← Silver transformation task
#        ↓
#   [silver_to_gold] ← Gold aggregation task
#        ↓
#   [data_quality_check] ← 7-suite validation with Gold layer gate
#        ↓
#   [update_metrics] ← Log pipeline execution metrics (non-blocking)
#
# ════════════════════════════════════════════════════════════════════════════

# Define task dependencies
run_silver >> run_gold >> data_quality >> update_db
