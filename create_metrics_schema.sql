-- ============================================================================
-- DAY 7: METRICS SCHEMA FOR MONITORING
-- ============================================================================
-- Creates tables to store pipeline metrics for Grafana dashboards
-- ============================================================================

-- Create metrics schema
CREATE SCHEMA IF NOT EXISTS metrics;

-- =============================================================================
-- TABLE 1: Pipeline Metrics (Time-Series Data)
-- =============================================================================
-- Stores numerical metrics over time (events processed, rates, etc.)

CREATE TABLE IF NOT EXISTS metrics.pipeline_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit VARCHAR(20),  -- 'count', 'percent', 'seconds', 'bytes'
    tags JSONB,  -- Additional dimensions: {"layer": "silver", "event_type": "purchase"}
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Indexes for fast querying
    CONSTRAINT valid_metric_name CHECK (metric_name ~ '^[a-z0-9_.]+$')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_name_time 
    ON metrics.pipeline_metrics(metric_name, recorded_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_time 
    ON metrics.pipeline_metrics(recorded_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_tags 
    ON metrics.pipeline_metrics USING GIN (tags);

COMMENT ON TABLE metrics.pipeline_metrics IS 'Time-series metrics for pipeline monitoring';
COMMENT ON COLUMN metrics.pipeline_metrics.metric_name IS 'Dot-separated metric name (e.g., pipeline.events.processed)';
COMMENT ON COLUMN metrics.pipeline_metrics.metric_value IS 'Numerical value of the metric';
COMMENT ON COLUMN metrics.pipeline_metrics.tags IS 'JSON object with additional dimensions';

-- =============================================================================
-- TABLE 2: Pipeline Runs (Job Execution History)
-- =============================================================================
-- Tracks each pipeline execution with status and duration

CREATE TABLE IF NOT EXISTS metrics.pipeline_runs (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    run_id VARCHAR(100) UNIQUE,  -- Unique identifier for this run
    status VARCHAR(20) NOT NULL,  -- 'running', 'success', 'failed', 'timeout'
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER,  -- Calculated: completed_at - started_at
    events_processed INTEGER,
    events_failed INTEGER,
    error_message TEXT,
    metadata JSONB,  -- Additional run information
    
    CONSTRAINT valid_status CHECK (status IN ('running', 'success', 'failed', 'timeout'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_name_time 
    ON metrics.pipeline_runs(pipeline_name, started_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status 
    ON metrics.pipeline_runs(status, started_at DESC);

COMMENT ON TABLE metrics.pipeline_runs IS 'Execution history of pipeline jobs';
COMMENT ON COLUMN metrics.pipeline_runs.run_id IS 'Unique identifier (e.g., Airflow run_id or timestamp)';

-- =============================================================================
-- TABLE 3: Data Quality Metrics
-- =============================================================================
-- Stores data quality check results

CREATE TABLE IF NOT EXISTS metrics.data_quality_checks (
    id SERIAL PRIMARY KEY,
    check_name VARCHAR(100) NOT NULL,
    dataset VARCHAR(100) NOT NULL,  -- 'bronze.clickstream', 'silver.clickstream'
    check_type VARCHAR(50) NOT NULL,  -- 'schema', 'null', 'range', 'uniqueness'
    status VARCHAR(20) NOT NULL,  -- 'passed', 'warning', 'failed'
    records_checked INTEGER,
    records_failed INTEGER,
    failure_rate NUMERIC(5,2),  -- Percentage
    details JSONB,  -- Specific failures
    checked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_dq_status CHECK (status IN ('passed', 'warning', 'failed'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dq_checks_dataset_time 
    ON metrics.data_quality_checks(dataset, checked_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_dq_checks_status 
    ON metrics.data_quality_checks(status, checked_at DESC);

COMMENT ON TABLE metrics.data_quality_checks IS 'Data quality validation results';

-- =============================================================================
-- TABLE 4: System Resource Metrics
-- =============================================================================
-- Stores system resource usage (CPU, memory, disk)

CREATE TABLE IF NOT EXISTS metrics.system_resources (
    id SERIAL PRIMARY KEY,
    host VARCHAR(100) NOT NULL,  -- 'spark-driver', 'kafka', 'postgres'
    resource_type VARCHAR(50) NOT NULL,  -- 'cpu', 'memory', 'disk', 'network'
    metric_name VARCHAR(100) NOT NULL,  -- 'cpu.percent', 'memory.used.bytes'
    metric_value NUMERIC NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_system_resources_host_time 
    ON metrics.system_resources(host, resource_type, recorded_at DESC);

COMMENT ON TABLE metrics.system_resources IS 'System resource utilization metrics';

-- =============================================================================
-- TABLE 5: Business Metrics
-- =============================================================================
-- Stores business-level KPIs (revenue, conversions, etc.)

CREATE TABLE IF NOT EXISTS metrics.business_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    dimension VARCHAR(100),  -- 'product_category', 'device_type', 'region'
    dimension_value VARCHAR(100),  -- 'electronics', 'mobile', 'US'
    time_period VARCHAR(20),  -- 'hourly', 'daily', 'monthly'
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_business_metrics_name_period 
    ON metrics.business_metrics(metric_name, period_start DESC);

COMMENT ON TABLE metrics.business_metrics IS 'Business KPIs and metrics';

-- =============================================================================
-- TABLE 6: Alerts
-- =============================================================================
-- Tracks alerts that have been triggered

CREATE TABLE IF NOT EXISTS metrics.alerts (
    id SERIAL PRIMARY KEY,
    alert_name VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,  -- 'critical', 'warning', 'info'
    status VARCHAR(20) NOT NULL,  -- 'firing', 'resolved'
    message TEXT NOT NULL,
    metric_name VARCHAR(100),
    threshold_value NUMERIC,
    actual_value NUMERIC,
    triggered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    notified BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'warning', 'info')),
    CONSTRAINT valid_alert_status CHECK (status IN ('firing', 'resolved'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_alerts_status_time 
    ON metrics.alerts(status, triggered_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_alerts_severity 
    ON metrics.alerts(severity, triggered_at DESC);

COMMENT ON TABLE metrics.alerts IS 'Alert history and current active alerts';

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- View: Latest metrics (last value for each metric)
CREATE OR REPLACE VIEW metrics.latest_metrics AS
SELECT DISTINCT ON (metric_name)
    metric_name,
    metric_value,
    metric_unit,
    tags,
    recorded_at
FROM metrics.pipeline_metrics
ORDER BY metric_name, recorded_at DESC;

COMMENT ON VIEW metrics.latest_metrics IS 'Most recent value for each metric';

-- View: Pipeline health summary
CREATE OR REPLACE VIEW metrics.pipeline_health AS
SELECT 
    pipeline_name,
    COUNT(*) FILTER (WHERE status = 'success') AS successful_runs,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
    COUNT(*) FILTER (WHERE status = 'running') AS running_runs,
    AVG(duration_seconds) FILTER (WHERE status = 'success') AS avg_duration_sec,
    MAX(started_at) AS last_run_time
FROM metrics.pipeline_runs
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY pipeline_name;

COMMENT ON VIEW metrics.pipeline_health IS '24-hour pipeline health summary';

-- View: Active alerts
CREATE OR REPLACE VIEW metrics.active_alerts AS
SELECT 
    alert_name,
    severity,
    message,
    actual_value,
    threshold_value,
    triggered_at,
    NOW() - triggered_at AS duration
FROM metrics.alerts
WHERE status = 'firing'
ORDER BY severity, triggered_at DESC;

COMMENT ON VIEW metrics.active_alerts IS 'Currently firing alerts';

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function: Record a metric
CREATE OR REPLACE FUNCTION metrics.record_metric(
    p_metric_name VARCHAR,
    p_metric_value NUMERIC,
    p_metric_unit VARCHAR DEFAULT NULL,
    p_tags JSONB DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO metrics.pipeline_metrics (metric_name, metric_value, metric_unit, tags)
    VALUES (p_metric_name, p_metric_value, p_metric_unit, p_tags)
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION metrics.record_metric IS 'Helper function to record a metric';

-- Function: Get metric rate (change per second)
CREATE OR REPLACE FUNCTION metrics.get_metric_rate(
    p_metric_name VARCHAR,
    p_interval INTERVAL DEFAULT '5 minutes'
)
RETURNS NUMERIC AS $$
DECLARE
    v_latest NUMERIC;
    v_previous NUMERIC;
    v_time_diff NUMERIC;
BEGIN
    -- Get latest value
    SELECT metric_value INTO v_latest
    FROM metrics.pipeline_metrics
    WHERE metric_name = p_metric_name
    ORDER BY recorded_at DESC
    LIMIT 1;
    
    -- Get value from interval ago
    SELECT metric_value INTO v_previous
    FROM metrics.pipeline_metrics
    WHERE metric_name = p_metric_name
      AND recorded_at <= NOW() - p_interval
    ORDER BY recorded_at DESC
    LIMIT 1;
    
    -- Calculate rate
    IF v_previous IS NOT NULL THEN
        v_time_diff := EXTRACT(EPOCH FROM p_interval);
        RETURN (v_latest - v_previous) / v_time_diff;
    ELSE
        RETURN NULL;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION metrics.get_metric_rate IS 'Calculate rate of change for a metric';

-- =============================================================================
-- SAMPLE DATA (for testing)
-- =============================================================================

-- Insert sample metrics
INSERT INTO metrics.pipeline_metrics (metric_name, metric_value, metric_unit, tags)
VALUES
    ('pipeline.events.total', 16783, 'count', '{"layer": "silver"}'::jsonb),
    ('pipeline.events.rate', 50, 'events_per_sec', '{"layer": "bronze"}'::jsonb),
    ('pipeline.latency.p95', 8.5, 'seconds', '{"layer": "bronze"}'::jsonb),
    ('pipeline.error.rate', 0.2, 'percent', NULL),
    ('business.conversion.rate', 4.0, 'percent', '{"funnel": "search_to_purchase"}'::jsonb);

-- Insert sample pipeline run
INSERT INTO metrics.pipeline_runs (pipeline_name, run_id, status, duration_seconds, events_processed, events_failed)
VALUES
    ('ecommerce_pipeline', 'run_20240115_1000', 'success', 320, 16783, 33),
    ('ecommerce_pipeline', 'run_20240115_1600', 'success', 315, 16890, 28);

-- Insert sample data quality check
INSERT INTO metrics.data_quality_checks (check_name, dataset, check_type, status, records_checked, records_failed, failure_rate)
VALUES
    ('null_check_user_id', 'silver.clickstream', 'null', 'passed', 16783, 0, 0.00),
    ('range_check_price', 'silver.clickstream', 'range', 'warning', 16783, 12, 0.07);

GRANT ALL ON SCHEMA metrics TO dataeng;
GRANT ALL ON ALL TABLES IN SCHEMA metrics TO dataeng;
GRANT ALL ON ALL SEQUENCES IN SCHEMA metrics TO dataeng;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA metrics TO dataeng;

-- Success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ Metrics schema created successfully!';
    RAISE NOTICE '   Tables: pipeline_metrics, pipeline_runs, data_quality_checks, system_resources, business_metrics, alerts';
    RAISE NOTICE '   Views: latest_metrics, pipeline_health, active_alerts';
    RAISE NOTICE '   Functions: record_metric(), get_metric_rate()';
END $$;
