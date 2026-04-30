"""
EVENT SCHEMAS
=============

This module defines the structure of all events in our system.

WHY SCHEMAS ARE CRITICAL:
1. Contract between producer and consumer (like API spec)
2. Documentation (what fields exist, what do they mean?)
3. Validation (catch errors early)
4. Evolution (v1 → v2 without breaking things)

INTERVIEW TIP:
"I design schemas with versioning, clear field naming, and documentation. 
I consider both current needs and future evolution. I use JSON for flexibility 
while maintaining structure through validation."

CONCEPTS COVERED:
- Schema design principles
- Field naming conventions
- Data types selection
- Required vs optional fields
- Schema versioning
- Event metadata
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


# ============================================================================
# SCHEMA VERSION
# ============================================================================
#
# CONCEPT: Schema Versioning
# - v1 → v2 → v3 as requirements change
# - Consumers can handle multiple versions
# - Backward compatibility is key
#
# WHY?
# - Can't update all consumers at once (different teams, different timelines)
# - Need to support old clients while rolling out new schema
# - Allows A/B testing of schema changes
#

SCHEMA_VERSION = "1.0.0"


# ============================================================================
# ENUMS FOR TYPE SAFETY
# ============================================================================
#
# CONCEPT: Enums
# - Predefined set of valid values
# - Catches typos at development time
# - Self-documenting (IDE shows valid options)
#
# Example: event_type = EventType.PAGE_VIEW (not "page_view" string)
# Typo "page_veiw" caught immediately vs runtime error
#

class EventType(Enum):
    """
    All possible event types in clickstream.
    
    CONCEPT: User Journey Events
    These represent the funnel from awareness to purchase.
    """
    SEARCH = "search"                    # User searches for product
    PAGE_VIEW = "page_view"              # User views product page
    ADD_TO_CART = "add_to_cart"          # User adds item to cart
    REMOVE_FROM_CART = "remove_from_cart"  # User removes item from cart
    CHECKOUT_STARTED = "checkout_started"  # User begins checkout
    CHECKOUT_COMPLETED = "checkout_completed"  # Purchase completed
    WISHLIST_ADD = "wishlist_add"        # User saves for later
    REVIEW_SUBMITTED = "review_submitted"  # User writes review
    FILTER_APPLIED = "filter_applied"    # User filters search results
    SORT_CHANGED = "sort_changed"        # User changes sort order


class DeviceType(Enum):
    """Device categories for analytics."""
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"


class PaymentMethod(Enum):
    """Payment methods supported."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank_transfer"


class OrderStatus(Enum):
    """Transaction lifecycle states."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


# ============================================================================
# BASE EVENT CLASS
# ============================================================================
#
# CONCEPT: Inheritance
# - Common fields shared by all events
# - DRY (Don't Repeat Yourself)
# - Ensures consistency
#
# WHY @dataclass?
# - Automatic __init__, __repr__, __eq__
# - Type hints enforced
# - Less boilerplate code
# - Python 3.7+ standard for data structures
#

@dataclass
class BaseEvent:
    """
    Base class for all events with common metadata.
    
    CONCEPT: Event Metadata
    Every event needs:
    - Unique ID (for deduplication, debugging)
    - Timestamp (for ordering, time-based analytics)
    - Schema version (for evolution)
    - Source system (for troubleshooting)
    
    WHY event_id?
    - Deduplication: If same event arrives twice, detect it
    - Debugging: "Show me event abc123"
    - Tracing: Follow event through entire pipeline
    
    WHY timestamp?
    - Event time (when it happened) vs processing time (when we see it)
    - Windowing: "Events in last 5 minutes"
    - Ordering: Process events in sequence
    
    WHY schema_version?
    - Consumer knows how to parse this event
    - Can route v1 and v2 to different processors
    - Enables gradual migration
    """
    
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    # CONCEPT: UUID (Universally Unique Identifier)
    # - Guaranteed unique across all events (even across machines)
    # - No coordination needed (unlike auto-increment IDs)
    # - Can generate offline
    # Format: evt_a1b2c3d4e5f6g7h8 (prefix + 16 hex chars)
    
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    # CONCEPT: ISO 8601 Format
    # - Standard: 2024-02-07T10:30:45.123Z
    # - 'Z' means UTC (no timezone confusion)
    # - Sortable as string
    # - Parseable by all languages
    # WHY UTC? No timezone issues, standard reference
    
    schema_version: str = field(default=SCHEMA_VERSION)
    # CONCEPT: Semantic Versioning
    # - MAJOR.MINOR.PATCH (1.0.0)
    # - MAJOR: Breaking changes
    # - MINOR: New fields (backward compatible)
    # - PATCH: Bug fixes
    
    source_system: str = field(default="data-generator")
    # CONCEPT: System Identification
    # - Which system produced this event?
    # - Useful when multiple sources produce same event type
    # - Enables source-specific logic or filtering
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert dataclass to dictionary for JSON serialization.
        
        CONCEPT: Serialization
        - Python object → JSON string → Kafka message
        - Must be JSON-serializable (no datetime objects, only primitives)
        
        Returns:
            dict: JSON-serializable dictionary
        """
        result = asdict(self)
        
        # Convert Enums to their string values
        # CONCEPT: Enum handling in JSON
        # Enum.MOBILE → "mobile" (JSON doesn't have Enum type)
        for key, value in result.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif value is None:
                # CONCEPT: Null handling
                # Keep nulls (don't remove) - indicates field exists but no value
                # Removing would lose information: "field not sent" vs "field sent as null"
                pass
        
        return result


# ============================================================================
# CLICKSTREAM EVENT
# ============================================================================
#
# CONCEPT: Clickstream Data
# - Every user interaction on website/app
# - Foundation for analytics, ML, personalization
# - High volume, lower value per event
#
# REAL-WORLD VOLUME:
# - Medium site: 100-1000 events/sec
# - Large site: 100,000+ events/sec
# - Retention: Usually 7-30 days (large volume)
#

@dataclass
class ClickstreamEvent(BaseEvent):
    """
    User interaction event (clicks, views, searches, etc.)
    
    SCHEMA DESIGN PRINCIPLES:
    1. Required fields: Can't be null (user_id, event_type, session_id)
    2. Optional fields: Can be null (product_id - not all events have a product)
    3. Rich context: Device, location, referrer (for segmentation)
    4. Performance data: Page load time (for optimization)
    """
    
    # === IDENTITY (REQUIRED) ===
    user_id: str = ""
    session_id: str = ""
    event_type: str = ""
    device_type: str = ""
    
    # === PRODUCT INFORMATION (OPTIONAL) ===
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    price: Optional[float] = None
    
    # === SEARCH CONTEXT ===
    search_query: Optional[str] = None
    search_results_count: Optional[int] = None
    
    # === CART CONTEXT ===
    cart_total: Optional[float] = None
    cart_item_count: Optional[int] = None
    
    # === DEVICE & PLATFORM ===
    os: Optional[str] = None
    browser: Optional[str] = None
    screen_resolution: Optional[str] = None
    
    # === LOCATION ===
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    ip_address: Optional[str] = None
    
    # === REFERRAL & ATTRIBUTION ===
    referrer_url: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    
    # === PERFORMANCE ===
    page_load_time_ms: Optional[int] = None
    
    # === USER AGENT ===
    user_agent: Optional[str] = None
    
    # === EXPERIMENT TRACKING ===
    ab_test_variant: Optional[str] = None
    
    def __post_init__(self):
        """
        Validation after initialization.
        
        CONCEPT: Data Validation
        - Catch invalid data at creation time
        - Better than runtime errors later in pipeline
        - Documents business rules
        """
        # Validate event_type is valid
        if isinstance(self.event_type, EventType):
            self.event_type = self.event_type.value
        
        # Validate device_type is valid
        if isinstance(self.device_type, DeviceType):
            self.device_type = self.device_type.value
        
        # Business rule: If add_to_cart, product_id is required
        if self.event_type in ['add_to_cart', 'remove_from_cart']:
            if not self.product_id:
                raise ValueError(f"product_id required for {self.event_type} events")
        
        # Business rule: If search, search_query is required
        if self.event_type == 'search':
            if not self.search_query:
                raise ValueError("search_query required for search events")


# ============================================================================
# TRANSACTION EVENT
# ============================================================================
#
# CONCEPT: Transaction Data
# - Purchase completed
# - Lower volume, higher value per event
# - Needs strong consistency (can't lose money!)
# - Retention: Forever (financial records)
#

@dataclass
class TransactionEvent(BaseEvent):
    """
    Completed purchase transaction.
    
    BUSINESS CRITICAL:
    - Financial records (must be accurate)
    - Drives revenue reports
    - Used for reconciliation
    - Legal requirement to retain
    """
    
    # === REQUIRED FIELDS ===
    transaction_id: str = ""
    order_id: str = ""
    user_id: str = ""
    customer_tier: str = ""
    subtotal_cents: int = 0
    tax_cents: int = 0
    shipping_cents: int = 0
    discount_cents: int = 0
    total_cents: int = 0
    total_items: int = 0
    payment_method: str = ""
    order_status: str = ""
    
    # === OPTIONAL FIELDS ===
    currency: str = "USD"
    items: List[Dict[str, Any]] = field(default_factory=list)
    payment_processor: Optional[str] = None
    payment_processor_transaction_id: Optional[str] = None
    shipping_method: Optional[str] = None
    shipping_address: Optional[Dict[str, str]] = None
    estimated_delivery_date: Optional[str] = None
    promo_codes: Optional[List[str]] = None
    discount_percentage: Optional[float] = None
    discount_reason: Optional[str] = None
    session_id: Optional[str] = None
    device_type: Optional[str] = None
    country: Optional[str] = None
    order_created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    payment_completed_at: Optional[str] = None
    
    def __post_init__(self):
        """Validation for transaction events."""
        # Validate money math
        calculated_total = (
            self.subtotal_cents + 
            self.tax_cents + 
            self.shipping_cents - 
            self.discount_cents
        )
        
        if calculated_total != self.total_cents:
            raise ValueError(
                f"Total mismatch: calculated {calculated_total} != actual {self.total_cents}"
            )
        
        # Validate has items
        if not self.items or len(self.items) == 0:
            raise ValueError("Transaction must have at least one item")
        
        # Convert enums to values
        if isinstance(self.payment_method, PaymentMethod):
            self.payment_method = self.payment_method.value
        if isinstance(self.order_status, OrderStatus):
            self.order_status = self.order_status.value


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_sample_clickstream() -> ClickstreamEvent:
    """
    Create a sample clickstream event for testing.
    
    CONCEPT: Factory Functions
    - Easily create test data
    - Documents example usage
    - Useful in unit tests
    """
    return ClickstreamEvent(
        user_id="usr_sample123",
        session_id="sess_sample456",
        event_type=EventType.PAGE_VIEW.value,
        product_id="prod_001",
        product_name="Wireless Headphones",
        category="Electronics",
        price=99.99,
        device_type=DeviceType.MOBILE.value,
        country="US"
    )


def create_sample_transaction() -> TransactionEvent:
    """Create a sample transaction event for testing."""
    return TransactionEvent(
        transaction_id="txn_sample789",
        order_id="ord_sample456",
        user_id="usr_sample123",
        customer_tier="regular",
        subtotal_cents=9999,  # $99.99
        tax_cents=800,        # $8.00
        shipping_cents=500,   # $5.00
        discount_cents=0,
        total_cents=11299,    # $112.99
        items=[
            {
                "product_id": "prod_001",
                "product_name": "Wireless Headphones",
                "quantity": 1,
                "price_cents": 9999,
                "category": "Electronics"
            }
        ],
        total_items=1,
        payment_method=PaymentMethod.CREDIT_CARD.value,
        order_status=OrderStatus.CONFIRMED.value
    )


# ============================================================================
# SCHEMA DOCUMENTATION
# ============================================================================

def print_schema_docs():
    """
    Print schema documentation for reference.
    
    CONCEPT: Self-Documenting Code
    - Schema serves as its own documentation
    - Generate docs from code (single source of truth)
    """
    print("=== CLICKSTREAM EVENT SCHEMA ===")
    print("Required fields:")
    print("  - user_id, session_id, event_type, device_type")
    print("Optional fields:")
    print("  - product_id, search_query, location, etc.")
    print("\n=== TRANSACTION EVENT SCHEMA ===")
    print("Required fields:")
    print("  - transaction_id, order_id, user_id, financial_details, items")
    print("Optional fields:")
    print("  - shipping_details, promo_codes, session_id")


# ============================================================================
# SUMMARY
# ============================================================================
#
# This module defines:
# 1. BaseEvent: Common fields for all events
# 2. ClickstreamEvent: User interaction tracking
# 3. TransactionEvent: Purchase records
# 4. Enums: Type-safe value sets
# 5. Validation: Business rules enforced at creation
#
# INTERVIEW TALKING POINTS:
# - "I use dataclasses for type-safe event schemas"
# - "I version schemas to enable evolution without breaking consumers"
# - "I validate data at creation time to fail fast"
# - "I store money in cents to avoid floating point precision issues"
# - "I denormalize for event capture (price at time of event)"
# - "I use enums for type safety and self-documentation"
#
# NEXT FILE: generators.py (actually generate the events!)
#
# ============================================================================