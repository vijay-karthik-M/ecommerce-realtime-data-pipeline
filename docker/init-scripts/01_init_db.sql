-- ================================================================================
-- POSTGRESQL INITIALIZATION SCRIPT
-- ================================================================================
--
-- This script runs automatically when Postgres container starts for the first time.
-- It creates the initial database schema for our analytics tables.
--
-- WHY SEPARATE INIT SCRIPT?
-- - Version controlled schema (Infrastructure as Code)
-- - Automated setup (no manual SQL execution)
-- - Documented data model
--
-- ================================================================================

-- Create schema for organizing tables
-- Think of schemas as "folders" for tables
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS metrics;

-- Set default schema
SET search_path TO analytics, public;

-- ================================================================================
-- DIMENSION TABLES (Star Schema)
-- ================================================================================
--
-- CONCEPT: Dimensional Modeling
-- Fact tables (transactions) + Dimension tables (descriptive attributes)
-- Optimized for analytical queries (OLAP), not transactional (OLTP)
--
-- WHY Star Schema?
-- - Easy to understand (business users can query)
-- - Fast queries (pre-joined dimensions)
-- - Flexible (can add dimensions without changing facts)
--

-- Dimension: Date
-- Every date gets a row with pre-calculated attributes
-- WHY? Faster than calculating "is_weekend" in every query
CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_key INTEGER PRIMARY KEY,              -- YYYYMMDD format (e.g., 20240325)
    date_actual DATE NOT NULL,                 -- Actual date
    day_of_week INTEGER NOT NULL,              -- 1=Monday, 7=Sunday
    day_name VARCHAR(10) NOT NULL,             -- 'Monday', 'Tuesday', etc.
    day_of_month INTEGER NOT NULL,             -- 1-31
    day_of_year INTEGER NOT NULL,              -- 1-365
    week_of_year INTEGER NOT NULL,             -- 1-52
    month_actual INTEGER NOT NULL,             -- 1-12
    month_name VARCHAR(10) NOT NULL,           -- 'January', 'February', etc.
    quarter_actual INTEGER NOT NULL,           -- 1-4
    year_actual INTEGER NOT NULL,              -- 2024, 2025, etc.
    is_weekend BOOLEAN NOT NULL,               -- TRUE if Sat/Sun
    is_holiday BOOLEAN DEFAULT FALSE,          -- Flag for holidays
    fiscal_year INTEGER,                       -- For companies with non-calendar fiscal year
    fiscal_quarter INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fast date lookups
CREATE INDEX IF NOT EXISTS idx_dim_date_actual ON analytics.dim_date(date_actual);

COMMENT ON TABLE analytics.dim_date IS 'Date dimension for time-based analysis';

-- Dimension: Customer
-- Slowly Changing Dimension Type 2 (SCD2)
-- WHY SCD2? Track historical changes (customer moved, tier changed)
CREATE TABLE IF NOT EXISTS analytics.dim_customer (
    customer_key SERIAL PRIMARY KEY,           -- Surrogate key (auto-increment)
    customer_id VARCHAR(50) NOT NULL,          -- Natural key (actual customer ID)
    customer_name VARCHAR(200),
    email VARCHAR(200),
    customer_tier VARCHAR(20),                 -- 'Gold', 'Silver', 'Bronze'
    registration_date DATE,
    country VARCHAR(100),
    state VARCHAR(100),
    city VARCHAR(100),
    zip_code VARCHAR(20),
    -- SCD2 fields to track history
    effective_date DATE NOT NULL,              -- When this version became active
    expiration_date DATE,                      -- When this version expired (NULL = current)
    is_current BOOLEAN DEFAULT TRUE,           -- TRUE for current version only
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Composite index for lookups
CREATE INDEX IF NOT EXISTS idx_dim_customer_id_current 
    ON analytics.dim_customer(customer_id, is_current);

COMMENT ON TABLE analytics.dim_customer IS 'Customer dimension with SCD Type 2 for historical tracking';

-- Dimension: Product
CREATE TABLE IF NOT EXISTS analytics.dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(200),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    unit_price DECIMAL(10, 2),
    cost DECIMAL(10, 2),
    margin_percent DECIMAL(5, 2),               -- Pre-calculated margin %
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_product_category ON analytics.dim_product(category);
CREATE INDEX IF NOT EXISTS idx_dim_product_brand ON analytics.dim_product(brand);

COMMENT ON TABLE analytics.dim_product IS 'Product dimension with pricing and categorization';

-- ================================================================================
-- FACT TABLES (Transactions/Events)
-- ================================================================================
--
-- CONCEPT: Fact Tables
-- - Contain measurements/metrics (amounts, quantities, counts)
-- - Large tables (millions to billions of rows)
-- - Foreign keys to dimension tables
-- - Typically partitioned by date
--

-- Fact: Sales Transactions
CREATE TABLE IF NOT EXISTS analytics.fact_sales (
    sale_id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL UNIQUE,
    
    -- Foreign keys to dimensions
    date_key INTEGER REFERENCES analytics.dim_date(date_key),
    customer_key INTEGER REFERENCES analytics.dim_customer(customer_key),
    product_key INTEGER REFERENCES analytics.dim_product(product_key),
    
    -- Measurements (the "facts")
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,        -- quantity * unit_price - discount + tax
    
    -- Additional attributes
    payment_method VARCHAR(50),                   -- 'Credit Card', 'PayPal', etc.
    shipping_cost DECIMAL(10, 2) DEFAULT 0,
    transaction_timestamp TIMESTAMP NOT NULL,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50) DEFAULT 'kafka_stream'
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON analytics.fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON analytics.fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON analytics.fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_timestamp ON analytics.fact_sales(transaction_timestamp);

COMMENT ON TABLE analytics.fact_sales IS 'Sales transaction fact table with foreign keys to dimensions';

-- Fact: Clickstream Events
-- Different grain than sales (one row per click, not per transaction)
CREATE TABLE IF NOT EXISTS analytics.fact_clickstream (
    event_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    
    -- Foreign keys
    date_key INTEGER REFERENCES analytics.dim_date(date_key),
    customer_key INTEGER REFERENCES analytics.dim_customer(customer_key),
    product_key INTEGER REFERENCES analytics.dim_product(product_key),
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,              -- 'page_view', 'add_to_cart', 'search', etc.
    page_url TEXT,
    referrer_url TEXT,
    device_type VARCHAR(50),                      -- 'mobile', 'desktop', 'tablet'
    browser VARCHAR(50),
    
    -- Measurements
    time_on_page INTEGER,                         -- Seconds
    scroll_depth INTEGER,                         -- Percentage (0-100)
    
    -- Timestamps
    event_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clickstream_date ON analytics.fact_clickstream(date_key);
CREATE INDEX IF NOT EXISTS idx_clickstream_session ON analytics.fact_clickstream(session_id);
CREATE INDEX IF NOT EXISTS idx_clickstream_event_type ON analytics.fact_clickstream(event_type);

COMMENT ON TABLE analytics.fact_clickstream IS 'User clickstream events for behavioral analysis';

-- ================================================================================
-- AGGREGATE TABLES (Pre-calculated Metrics)
-- ================================================================================
--
-- WHY Aggregate Tables?
-- - Dashboards need fast response (can't scan millions of rows)
-- - Common queries pre-calculated and cached
-- - Trade-off: Storage space for query speed
--

-- Daily Sales Summary
CREATE TABLE IF NOT EXISTS analytics.agg_daily_sales (
    date_key INTEGER REFERENCES analytics.dim_date(date_key),
    total_sales DECIMAL(15, 2),
    total_orders INTEGER,
    total_customers INTEGER,
    total_products_sold INTEGER,
    average_order_value DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date_key)
);

COMMENT ON TABLE analytics.agg_daily_sales IS 'Daily aggregated sales metrics for dashboards';

-- Product Performance Summary
CREATE TABLE IF NOT EXISTS analytics.agg_product_performance (
    date_key INTEGER REFERENCES analytics.dim_date(date_key),
    product_key INTEGER REFERENCES analytics.dim_product(product_key),
    units_sold INTEGER,
    revenue DECIMAL(12, 2),
    num_customers INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date_key, product_key)
);

COMMENT ON TABLE analytics.agg_product_performance IS 'Daily product-level performance metrics';

-- ================================================================================
-- METRICS SCHEMA (Data Quality & Pipeline Health)
-- ================================================================================

-- Pipeline Execution Metrics
CREATE TABLE IF NOT EXISTS metrics.pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20),                           -- 'running', 'success', 'failed'
    rows_processed BIGINT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_name_time 
    ON metrics.pipeline_runs(pipeline_name, start_time DESC);

COMMENT ON TABLE metrics.pipeline_runs IS 'Track pipeline execution history and performance';

-- Data Quality Scores
CREATE TABLE IF NOT EXISTS metrics.data_quality_scores (
    score_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    check_date DATE NOT NULL,
    quality_score DECIMAL(5, 2),                  -- 0-100
    total_checks INTEGER,
    passed_checks INTEGER,
    failed_checks INTEGER,
    details JSONB,                                -- Store failure details in JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dq_scores_table_date 
    ON metrics.data_quality_scores(table_name, check_date DESC);

COMMENT ON TABLE metrics.data_quality_scores IS 'Daily data quality scores per table';

-- ================================================================================
-- STAGING SCHEMA (Temporary/Intermediate Data)
-- ================================================================================
--
-- WHY Staging Schema?
-- - Landing zone for raw data before transformation
-- - Can be truncated/reloaded without affecting production tables
-- - Useful for debugging
--

CREATE TABLE IF NOT EXISTS staging.raw_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_data JSONB NOT NULL,                    -- Store raw JSON
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE staging.raw_events IS 'Temporary storage for raw events before processing';

-- ================================================================================
-- HELPER FUNCTIONS
-- ================================================================================

-- Function to populate date dimension
-- This will fill dim_date with dates from 2024 to 2026
CREATE OR REPLACE FUNCTION analytics.populate_date_dimension(
    start_date DATE DEFAULT '2024-01-01',
    end_date DATE DEFAULT '2026-12-31'
)
RETURNS INTEGER AS $$
DECLARE
    loop_date DATE := start_date;
    rows_inserted INTEGER := 0;
BEGIN
    WHILE loop_date <= end_date LOOP
        INSERT INTO analytics.dim_date (
            date_key,
            date_actual,
            day_of_week,
            day_name,
            day_of_month,
            day_of_year,
            week_of_year,
            month_actual,
            month_name,
            quarter_actual,
            year_actual,
            is_weekend
        ) VALUES (
            TO_CHAR(loop_date, 'YYYYMMDD')::INTEGER,
            loop_date,
            EXTRACT(ISODOW FROM loop_date)::INTEGER,
            TO_CHAR(loop_date, 'Day'),
            EXTRACT(DAY FROM loop_date)::INTEGER,
            EXTRACT(DOY FROM loop_date)::INTEGER,
            EXTRACT(WEEK FROM loop_date)::INTEGER,
            EXTRACT(MONTH FROM loop_date)::INTEGER,
            TO_CHAR(loop_date, 'Month'),
            EXTRACT(QUARTER FROM loop_date)::INTEGER,
            EXTRACT(YEAR FROM loop_date)::INTEGER,
            EXTRACT(ISODOW FROM loop_date) IN (6, 7)
        )
        ON CONFLICT (date_key) DO NOTHING;
        
        loop_date := loop_date + INTERVAL '1 day';
        rows_inserted := rows_inserted + 1;
    END LOOP;
    
    RETURN rows_inserted;
END;
$$ LANGUAGE plpgsql;

-- Populate the date dimension
SELECT analytics.populate_date_dimension();

-- ================================================================================
-- GRANTS (Permissions)
-- ================================================================================

-- Grant permissions to dataeng user (our application user)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO dataeng;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO dataeng;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA metrics TO dataeng;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO dataeng;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA staging TO dataeng;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA metrics TO dataeng;

-- ================================================================================
-- SUMMARY
-- ================================================================================
--
-- SCHEMAS CREATED:
-- 1. analytics - Production tables (dimensions, facts, aggregates)
-- 2. staging - Temporary/intermediate data
-- 3. metrics - Pipeline monitoring and data quality
--
-- TABLES CREATED:
-- - 4 Dimension tables (date, customer, product, + SCD2 customer)
-- - 2 Fact tables (sales, clickstream)
-- - 2 Aggregate tables (daily sales, product performance)
-- - 2 Metrics tables (pipeline runs, data quality)
-- - 1 Staging table (raw events)
--
-- NEXT STEPS:
-- 1. Verify tables exist: \dt analytics.*
-- 2. Check date dimension populated: SELECT COUNT(*) FROM analytics.dim_date;
-- 3. Test insert: INSERT INTO staging.raw_events (event_data) VALUES ('{"test": true}');
--
-- ================================================================================
