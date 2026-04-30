"""
DATA GENERATOR CONFIGURATION
============================

This file contains all configuration settings, constants, and parameters for
our synthetic data generation.

WHY SEPARATE CONFIG FILE?
- Single source of truth (change once, affects everywhere)
- Easy to tune without touching logic
- Environment-specific settings (dev/staging/prod)
- Interview tip: "I separate configuration from logic for maintainability"

LEARNING CONCEPTS:
1. Probability distributions
2. Realistic conversion funnels
3. Temporal patterns
4. Category distributions
"""

import os
from datetime import datetime

# ============================================================================
# KAFKA CONFIGURATION
# ============================================================================
#
# CONCEPT: Bootstrap Servers
# - Initial contact point for Kafka cluster
# - Can be multiple (comma-separated) for redundancy
# - Format: "host1:port1,host2:port2"
#
# WHY localhost:9092?
# - Running Docker on same machine
# - From container perspective, host is accessible via host.docker.internal
# - But we're running Python on host, so localhost works
#

KAFKA_CONFIG = {
    'bootstrap_servers': ['localhost:9092'],
    # CONCEPT: bootstrap_servers can be a list for high availability
    # In production: ['kafka1:9092', 'kafka2:9092', 'kafka3:9092']
    
    'client_id': 'ecommerce-data-generator',
    # CONCEPT: Client ID helps identify this producer in Kafka logs/metrics
    # Useful for debugging: "Which application is producing this data?"
    
    'compression_type': 'gzip',
    # CONCEPT: Compress messages before sending (trade CPU for bandwidth)
    # Options: 'gzip' (good compression), 'snappy' (fast), 'lz4' (balanced)
    # Why gzip? Best compression ratio for our JSON messages
    
    'acks': 'all',
    # CONCEPT: Acknowledgment level (reliability vs performance)
    # 'all' = wait for all replicas to acknowledge (most reliable, slowest)
    # '1' = wait for leader only (balanced)
    # '0' = don't wait (fastest, can lose data)
    # We use 'all' for learning - in production, depends on requirements
    
    'retries': 3,
    # CONCEPT: Auto-retry failed sends
    # Network blips happen - retry before failing
    
    'max_in_flight_requests_per_connection': 1,
    # CONCEPT: How many requests can be sent before receiving acknowledgments
    # Must be 1 when using enable_idempotence=True for exactly-once semantics
    # Otherwise can allow up to 5 for better throughput
}

# ============================================================================
# KAFKA TOPICS
# ============================================================================
#
# CONCEPT: Topics
# - Like database tables, but for streaming data
# - Each topic stores a category of events
# - Consumers subscribe to topics they care about
#
# WHY SEPARATE TOPICS?
# - Different retention periods (clickstream = 7 days, transactions = forever)
# - Different consumers (ML team needs clickstream, finance needs transactions)
# - Different schemas (clickstream is sparse, transactions are dense)
#

TOPICS = {
    'clickstream': 'ecommerce.clickstream.v1',
    # NAMING CONVENTION: <domain>.<entity>.<version>
    # Why? Prevents conflicts, enables versioning, shows ownership
    
    'transactions': 'ecommerce.transactions.v1',
    # v1 = version 1 (when schema changes, create v2)
    
    'inventory': 'ecommerce.inventory.v1',
    # Future use: inventory updates
}

# ============================================================================
# DATA GENERATION RATES
# ============================================================================
#
# CONCEPT: Events per Second (throughput)
# - How fast we generate events
# - Should mimic real-world patterns
#
# REALISTIC E-COMMERCE NUMBERS:
# Small site: 10-100 events/sec
# Medium site: 100-1000 events/sec  
# Large site (Amazon): 100,000+ events/sec
#
# We'll use medium site numbers for learning
#

GENERATION_RATES = {
    'clickstream_per_second': 50,
    # CONCEPT: 50 user actions per second
    # = 3,000 per minute
    # = 180,000 per hour
    # = 4.3M per day
    # This is realistic for a mid-sized e-commerce site
    
    'transactions_per_second': 2,
    # CONCEPT: 2 purchases per second
    # = 120 per minute
    # = 7,200 per hour
    # = 172,800 per day
    # About $10M daily revenue if avg order = $60
    
    'batch_size': 100,
    # CONCEPT: Send N events at once (batching)
    # Why? More efficient than sending one-by-one
    # Kafka batches anyway, we just pre-batch
}

# ============================================================================
# TEMPORAL PATTERNS
# ============================================================================
#
# CONCEPT: Real traffic isn't constant - it has patterns
# - Peak hours (lunch, evening)
# - Quiet hours (3 AM)
# - Day of week patterns (more on weekends)
# - Seasonal patterns (Black Friday spike)
#
# WHY SIMULATE THIS?
# - Tests whether your pipeline handles variable load
# - More realistic data for ML models
# - Interview gold: "I simulate temporal patterns to test scalability"
#

# Hourly traffic multipliers (0.0 to 2.0)
# CONCEPT: Multiply base rate by these factors throughout the day
HOURLY_TRAFFIC_PATTERN = {
    0: 0.3,   # 12 AM - 1 AM: Very low (30% of base)
    1: 0.2,   # 1 AM - 2 AM: Lowest
    2: 0.2,   # 2 AM - 3 AM: Lowest
    3: 0.2,   # 3 AM - 4 AM: Lowest
    4: 0.3,   # 4 AM - 5 AM: Starting to rise
    5: 0.4,   # 5 AM - 6 AM: Early birds
    6: 0.6,   # 6 AM - 7 AM: Morning commute
    7: 0.8,   # 7 AM - 8 AM: Rising
    8: 1.0,   # 8 AM - 9 AM: Work starting
    9: 1.2,   # 9 AM - 10 AM: Peak morning
    10: 1.3,  # 10 AM - 11 AM: High
    11: 1.4,  # 11 AM - 12 PM: Pre-lunch peak
    12: 1.5,  # 12 PM - 1 PM: Lunch hour PEAK
    13: 1.3,  # 1 PM - 2 PM: Post-lunch
    14: 1.2,  # 2 PM - 3 PM: Afternoon
    15: 1.1,  # 3 PM - 4 PM: Afternoon
    16: 1.2,  # 4 PM - 5 PM: Pre-evening
    17: 1.4,  # 5 PM - 6 PM: Commute home
    18: 1.5,  # 6 PM - 7 PM: Evening PEAK
    19: 1.6,  # 7 PM - 8 PM: HIGHEST PEAK (people at home)
    20: 1.5,  # 8 PM - 9 PM: Evening
    21: 1.3,  # 9 PM - 10 PM: Winding down
    22: 1.0,  # 10 PM - 11 PM: Late evening
    23: 0.6,  # 11 PM - 12 AM: Going to bed
}

# Day of week multipliers
# CONCEPT: Shopping patterns differ by day
DAY_OF_WEEK_PATTERN = {
    0: 0.9,   # Monday: Slow start
    1: 1.0,   # Tuesday: Normal
    2: 1.0,   # Wednesday: Normal
    3: 1.1,   # Thursday: Building up
    4: 1.2,   # Friday: Payday shopping
    5: 1.4,   # Saturday: WEEKEND PEAK
    6: 1.3,   # Sunday: Weekend but preparing for week
}

# ============================================================================
# PRODUCT CATALOG
# ============================================================================
#
# CONCEPT: Realistic product distribution
# - Different categories have different popularity
# - Price ranges vary by category
# - Some products are seasonal
#

PRODUCT_CATEGORIES = {
    'Electronics': {
        'weight': 0.25,  # 25% of traffic (popular category)
        'price_range': (50, 2000),
        'avg_price': 500,
        'subcategories': ['Laptops', 'Phones', 'Tablets', 'Accessories', 'Smart Home'],
    },
    'Clothing': {
        'weight': 0.20,  # 20% of traffic
        'price_range': (10, 300),
        'avg_price': 60,
        'subcategories': ['Men', 'Women', 'Kids', 'Shoes', 'Accessories'],
    },
    'Home & Garden': {
        'weight': 0.15,
        'price_range': (20, 1000),
        'avg_price': 150,
        'subcategories': ['Furniture', 'Kitchen', 'Decor', 'Garden', 'Tools'],
    },
    'Books': {
        'weight': 0.10,
        'price_range': (5, 50),
        'avg_price': 15,
        'subcategories': ['Fiction', 'Non-Fiction', 'Textbooks', 'Comics', 'Magazines'],
    },
    'Sports & Outdoors': {
        'weight': 0.12,
        'price_range': (15, 800),
        'avg_price': 100,
        'subcategories': ['Fitness', 'Camping', 'Cycling', 'Water Sports', 'Team Sports'],
    },
    'Beauty & Health': {
        'weight': 0.10,
        'price_range': (8, 200),
        'avg_price': 35,
        'subcategories': ['Skincare', 'Makeup', 'Haircare', 'Vitamins', 'Personal Care'],
    },
    'Toys & Games': {
        'weight': 0.08,
        'price_range': (10, 150),
        'avg_price': 40,
        'subcategories': ['Action Figures', 'Board Games', 'Educational', 'Outdoor', 'Video Games'],
    },
}

# ============================================================================
# USER BEHAVIOR PATTERNS
# ============================================================================
#
# CONCEPT: Conversion Funnel
# - Not everyone who visits will buy
# - Progressive drop-off at each stage
# - This is REALISTIC - actual e-commerce conversion rates
#

CONVERSION_PROBABILITIES = {
    'search_to_view': 0.50,
    # CONCEPT: 50% of searches lead to viewing a product
    # Why not 100%? Sometimes search returns no results, or user quits
    
    'view_to_cart': 0.15,
    # CONCEPT: Only 15% of views lead to adding to cart
    # This is realistic! Most people browse without buying
    
    'cart_to_checkout': 0.60,
    # CONCEPT: 60% of cart additions lead to checkout attempt
    # Why not 100%? Cart abandonment (user changes mind, price too high, etc.)
    
    'checkout_to_purchase': 0.70,
    # CONCEPT: 70% of checkouts complete purchase
    # Why not 100%? Payment failures, shipping cost too high, changed mind
}

# OVERALL CONVERSION RATE = 0.50 * 0.15 * 0.60 * 0.70 = 0.0315 = 3.15%
# This means only 3.15% of searchers actually purchase
# This is VERY REALISTIC for e-commerce!

# Session duration patterns (in seconds)
SESSION_DURATION = {
    'min': 30,        # At least 30 seconds (quick visit)
    'avg': 600,       # Average 10 minutes (normal browsing)
    'max': 3600,      # Max 1 hour (deep browsing session)
}

# Items per session distribution
ITEMS_PER_SESSION = {
    'min': 1,
    'avg': 3,
    'max': 20,
}

# ============================================================================
# DEVICE DISTRIBUTION
# ============================================================================
#
# CONCEPT: Different devices have different usage patterns
# - Mobile dominates modern e-commerce (60%+)
# - Desktop still used for high-value purchases
# - Tablet somewhere in between
#

DEVICE_DISTRIBUTION = {
    'mobile': 0.60,     # 60% mobile (iOS + Android)
    'desktop': 0.30,    # 30% desktop (Windows + Mac)
    'tablet': 0.10,     # 10% tablet (iPad, etc.)
}

# Device-specific conversion rates
# CONCEPT: Desktop converts better (bigger screen, easier checkout)
DEVICE_CONVERSION_MULTIPLIER = {
    'mobile': 0.8,      # 20% lower conversion on mobile
    'desktop': 1.2,     # 20% higher conversion on desktop
    'tablet': 1.0,      # Average conversion
}

# ============================================================================
# CUSTOMER SEGMENTS
# ============================================================================
#
# CONCEPT: Not all customers are equal
# - VIP customers buy more frequently
# - New customers browse more, buy less
# - Regular customers in between
#

CUSTOMER_TIERS = {
    'new': {
        'weight': 0.40,           # 40% of users are new
        'purchase_probability': 0.02,   # Only 2% convert (trying site)
        'avg_order_value_multiplier': 0.8,
    },
    'regular': {
        'weight': 0.50,           # 50% are regular
        'purchase_probability': 0.05,   # 5% conversion (trust built)
        'avg_order_value_multiplier': 1.0,
    },
    'vip': {
        'weight': 0.10,           # 10% are VIP (80/20 rule)
        'purchase_probability': 0.15,   # 15% conversion (high intent)
        'avg_order_value_multiplier': 2.0,  # Spend 2x more
    },
}

# ============================================================================
# PAYMENT METHODS
# ============================================================================

PAYMENT_METHODS = {
    'credit_card': 0.50,
    'debit_card': 0.20,
    'paypal': 0.15,
    'apple_pay': 0.08,
    'google_pay': 0.05,
    'bank_transfer': 0.02,
}

# ============================================================================
# GEOGRAPHICAL DISTRIBUTION
# ============================================================================
#
# CONCEPT: Traffic comes from different regions
# - Affects shipping costs, delivery times
# - Different regions have different preferences
#

COUNTRY_DISTRIBUTION = {
    'US': 0.40,
    'UK': 0.15,
    'Canada': 0.10,
    'Germany': 0.08,
    'France': 0.07,
    'Australia': 0.06,
    'India': 0.05,
    'Japan': 0.05,
    'Brazil': 0.04,
}

# ============================================================================
# DATA QUALITY PARAMETERS
# ============================================================================
#
# CONCEPT: Real data is MESSY
# - Some fields occasionally missing (user didn't log in)
# - Some events malformed (network issues)
# - This tests our data quality framework!
#

DATA_QUALITY = {
    'null_rate': 0.01,
    # CONCEPT: 1% of non-required fields will be null
    # Why? Real data has missing values (user not logged in, optional fields)
    
    'duplicate_rate': 0.005,
    # CONCEPT: 0.5% of events will be duplicates
    # Why? Network retries, bugs in tracking code
    
    'late_arrival_rate': 0.02,
    # CONCEPT: 2% of events arrive late (timestamp in past)
    # Why? Mobile devices sync when they get connectivity
    
    'malformed_rate': 0.001,
    # CONCEPT: 0.1% of events are malformed (missing required fields)
    # Why? Bugs, schema evolution, client-side errors
}

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================

OUTPUT = {
    'log_level': 'INFO',
    # Options: DEBUG, INFO, WARNING, ERROR
    
    'log_interval': 100,
    # Log statistics every N events
    
    'metrics_port': 8000,
    # Expose Prometheus metrics on this port
}

# ============================================================================
# RUNTIME CONFIGURATION
# ============================================================================

RUNTIME = {
    'duration_seconds': None,
    # None = run forever, or specify seconds (3600 = 1 hour)
    
    'max_events': None,
    # None = unlimited, or specify max events to generate
    
    'seed': 42,
    # CONCEPT: Random seed for reproducibility
    # Same seed = same data (useful for testing)
}

# ============================================================================
# DERIVED CALCULATIONS
# ============================================================================
#
# CONCEPT: Calculate values based on config
# Don't hardcode - derive from base values
#

def get_current_traffic_multiplier():
    """
    Calculate current traffic multiplier based on time of day and day of week.
    
    Returns:
        float: Multiplier to apply to base event rate
    
    Example:
        If base rate is 50 events/sec and it's 7 PM on Saturday:
        - Hourly multiplier: 1.6
        - Day multiplier: 1.4
        - Total: 50 * 1.6 * 1.4 = 112 events/sec
    """
    now = datetime.now()
    hour = now.hour
    day_of_week = now.weekday()
    
    hourly_mult = HOURLY_TRAFFIC_PATTERN.get(hour, 1.0)
    daily_mult = DAY_OF_WEEK_PATTERN.get(day_of_week, 1.0)
    
    return hourly_mult * daily_mult


def get_effective_rate(base_rate):
    """
    Get current effective event generation rate.
    
    Args:
        base_rate (int): Base events per second
    
    Returns:
        int: Actual events per second considering temporal patterns
    """
    multiplier = get_current_traffic_multiplier()
    return int(base_rate * multiplier)


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config():
    """
    Validate configuration makes sense.
    Catches errors before they cause runtime issues.
    """
    # Check probability distributions sum to ~1.0
    assert abs(sum(PRODUCT_CATEGORIES[cat]['weight'] for cat in PRODUCT_CATEGORIES) - 1.0) < 0.01, \
        "Product category weights must sum to 1.0"
    
    assert abs(sum(DEVICE_DISTRIBUTION.values()) - 1.0) < 0.01, \
        "Device distribution must sum to 1.0"
    
    assert abs(sum(CUSTOMER_TIERS[tier]['weight'] for tier in CUSTOMER_TIERS) - 1.0) < 0.01, \
        "Customer tier weights must sum to 1.0"
    
    # Check rates are positive
    assert GENERATION_RATES['clickstream_per_second'] > 0, "Rate must be positive"
    assert GENERATION_RATES['transactions_per_second'] > 0, "Rate must be positive"
    
    print("✓ Configuration validated successfully")


# Validate on import
validate_config()

# ============================================================================
# SUMMARY
# ============================================================================
#
# This config file defines:
# 1. Kafka connection settings
# 2. Topic names
# 3. Event generation rates
# 4. Temporal patterns (hourly, daily)
# 5. Product catalog
# 6. User behavior patterns (conversion funnels)
# 7. Device and geographic distributions
# 8. Data quality parameters
#
# INTERVIEW TALKING POINTS:
# - "I use configuration files to separate concerns and enable easy tuning"
# - "I model realistic patterns like conversion funnels and temporal traffic"
# - "I validate configuration on startup to catch errors early"
# - "I derive values programmatically rather than hardcoding"
#
# NEXT FILE: schemas.py (define event structures)
#
# ============================================================================
