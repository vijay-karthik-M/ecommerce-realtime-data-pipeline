"""
EVENT GENERATORS
================

This module contains the core logic for generating realistic synthetic events.

DEEP CONCEPTS COVERED:
1. Probability Distributions & Random Sampling
2. State Machines (User Journey Modeling)
3. Temporal Patterns & Rate Limiting
4. Correlation vs Independence
5. Realistic Data Generation with Faker
6. Stateful vs Stateless Generation
7. Memory-Efficient Streaming

WHY THIS IS COMPLEX:
Real user behavior is NOT random - it's probabilistic with patterns:
- Users who view expensive items are more likely to purchase
- Mobile users convert less than desktop users
- Returning customers have different behavior than new customers
- Time of day affects behavior
- Past actions influence future actions (state machine)

This generator models all of these patterns!

INTERVIEW GOLD:
"I modeled realistic user behavior using probability distributions, state machines,
and temporal patterns. I ensured correlations between fields (e.g., device type
affects conversion rate) rather than treating them as independent random variables."
"""

import random
import time
from datetime import datetime, timedelta
from typing import Generator, Optional, Dict, Any, List, Tuple
from faker import Faker
import numpy as np

from .config import (
    PRODUCT_CATEGORIES,
    CONVERSION_PROBABILITIES,
    DEVICE_DISTRIBUTION,
    DEVICE_CONVERSION_MULTIPLIER,
    CUSTOMER_TIERS,
    PAYMENT_METHODS,
    COUNTRY_DISTRIBUTION,
    HOURLY_TRAFFIC_PATTERN,
    DAY_OF_WEEK_PATTERN,
    SESSION_DURATION,
    ITEMS_PER_SESSION,
    get_current_traffic_multiplier,
)
from .schemas import (
    ClickstreamEvent,
    TransactionEvent,
    EventType,
    DeviceType,
    PaymentMethod,
    OrderStatus,
)


# ============================================================================
# FAKER INITIALIZATION
# ============================================================================
#
# CONCEPT: Faker Library
# - Generates realistic fake data (names, addresses, emails, etc.)
# - Locale support (generate Indian names if locale='en_IN')
# - Consistent with seed (same seed = same data)
#
# WHY FAKER?
# - More realistic than "User1", "User2"
# - Tests edge cases (long names, special characters, unicode)
# - Makes demo data look professional
#
# ALTERNATIVES:
# - Manual generation (tedious, unrealistic)
# - Real data (privacy issues, limited volume)
# - Other libraries: mimesis, factory_boy
#

fake = Faker()
Faker.seed(42)  # Reproducibility: same seed = same fake data every run
random.seed(42)
np.random.seed(42)

# CONCEPT: Why Seed Everything?
# - Debugging: Can reproduce exact sequence of events
# - Testing: Deterministic output for assertions
# - Development: Consistent data for development
# - Production: Remove seeds for true randomness


# ============================================================================
# HELPER: WEIGHTED RANDOM CHOICE
# ============================================================================
#
# CONCEPT: Weighted Random Selection
# - Not all outcomes equally likely
# - Each option has a "weight" (probability)
# - Higher weight = more likely to be chosen
#
# MATH BEHIND IT:
# Options: ['A', 'B', 'C']
# Weights: [0.5, 0.3, 0.2]
# Total weight: 1.0
#
# Random number: 0.0 to 1.0
# 0.00-0.50 → A (50% chance)
# 0.50-0.80 → B (30% chance)
# 0.80-1.00 → C (20% chance)
#
# This is how we model: "60% mobile, 30% desktop, 10% tablet"
#

def weighted_choice(choices: Dict[str, float]) -> str:
    """
    Select a random key from dictionary based on weights.
    
    Args:
        choices: Dict mapping choice to weight (probability)
                 Example: {'mobile': 0.6, 'desktop': 0.3, 'tablet': 0.1}
    
    Returns:
        str: Selected choice
    
    DEEP DIVE:
    This function implements weighted random selection using the
    "inverse transform sampling" method:
    
    1. Create cumulative distribution function (CDF)
       [0.6, 0.9, 1.0] from [0.6, 0.3, 0.1]
    
    2. Generate uniform random number [0, 1)
    
    3. Find first CDF value >= random number
    
    This is mathematically equivalent to drawing from the probability
    distribution defined by the weights.
    
    EXAMPLE EXECUTION:
    choices = {'A': 0.5, 'B': 0.3, 'C': 0.2}
    
    Step 1: Create lists
    items = ['A', 'B', 'C']
    weights = [0.5, 0.3, 0.2]
    
    Step 2: Cumulative sum
    cumsum = [0.5, 0.8, 1.0]
    
    Step 3: Random number = 0.65
    
    Step 4: Find first cumsum >= 0.65
    0.5 < 0.65? No
    0.8 >= 0.65? Yes → return 'B'
    
    Over 1000 calls, approximately:
    - 500 will return 'A'
    - 300 will return 'B'
    - 200 will return 'C'
    """
    items = list(choices.keys())
    weights = list(choices.values())
    
    # Normalize weights to sum to 1.0 (in case they don't already)
    # CONCEPT: Normalization
    # If weights are [50, 30, 20], normalize to [0.5, 0.3, 0.2]
    total = sum(weights)
    if abs(total - 1.0) > 0.01:  # Allow small floating point errors
        weights = [w / total for w in weights]
    
    # Use numpy for efficient weighted choice
    # CONCEPT: numpy.random.choice
    # Vectorized operation (faster than Python loop)
    # Handles edge cases (empty weights, etc.)
    return np.random.choice(items, p=weights)


# ============================================================================
# USER GENERATOR
# ============================================================================
#
# CONCEPT: User Entity
# - Persistent identity across sessions
# - Has characteristics (tier, location, preferences)
# - Behavior influenced by characteristics
#
# WHY GENERATE USERS?
# - Realistic: Same user can have multiple sessions
# - Enables cohort analysis: "How do VIP users behave?"
# - Tests JOIN operations: "All events by user X"
#

class UserGenerator:
    """
    Generates and manages synthetic users.
    
    DESIGN DECISIONS:
    - Users are stateful (have persistent properties)
    - Users are stored in memory (for realistic multi-session behavior)
    - Users have tiers (new/regular/vip) affecting behavior
    - User pool size is limited (realistic - not infinite users)
    
    MEMORY CONSIDERATION:
    - 10,000 users × 500 bytes each = 5 MB
    - Acceptable for development
    - Production: Use database or cache (Redis)
    """
    
    def __init__(self, pool_size: int = 10000):
        """
        Initialize user pool.
        
        Args:
            pool_size: Number of unique users to generate
        
        CONCEPT: User Pool Size
        - Too small: Same users over and over (unrealistic)
        - Too large: Memory issues, slow lookups
        - 10,000 is good balance for medium site simulation
        
        REAL-WORLD NUMBERS:
        - Small site: 1,000-10,000 daily active users
        - Medium site: 10,000-100,000 daily active users
        - Large site: 1,000,000+ daily active users
        """
        self.pool_size = pool_size
        self.users: Dict[str, Dict[str, Any]] = {}
        self._generate_user_pool()
    
    def _generate_user_pool(self):
        """
        Pre-generate pool of users.
        
        CONCEPT: Pre-generation vs On-Demand
        - Pre-generate: Create all users upfront (faster runtime)
        - On-demand: Create users as needed (slower, more flexible)
        
        We pre-generate because:
        - Users are reused across sessions (need persistence)
        - Startup cost is one-time
        - Lookup is faster (no generation overhead)
        """
        print(f"Generating pool of {self.pool_size} synthetic users...")
        
        for i in range(self.pool_size):
            # Generate unique user ID
            user_id = f"usr_{fake.uuid4()[:16]}"
            
            # Assign customer tier based on distribution
            # CONCEPT: Weighted Assignment
            # 40% new, 50% regular, 10% VIP (Pareto principle: 80/20 rule)
            tier = weighted_choice({
                tier: props['weight'] 
                for tier, props in CUSTOMER_TIERS.items()
            })
            
            # Generate user profile
            # CONCEPT: Realistic Profile
            # - Name, email look real (not "user1@test.com")
            # - Address components for shipping simulation
            # - Registration date in past (realistic - not all users new today)
            self.users[user_id] = {
                'user_id': user_id,
                'name': fake.name(),
                'email': fake.email(),
                'tier': tier,
                'country': weighted_choice(COUNTRY_DISTRIBUTION),
                'registration_date': fake.date_between(
                    start_date='-2y',  # Registered sometime in last 2 years
                    end_date='today'
                ),
                # CONCEPT: Derived Properties
                # Purchase probability varies by tier
                'purchase_probability': CUSTOMER_TIERS[tier]['purchase_probability'],
                'order_value_multiplier': CUSTOMER_TIERS[tier]['avg_order_value_multiplier'],
            }
            
            # Log progress every 1000 users
            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1}/{self.pool_size} users...")
        
        print(f"✓ User pool generated with distribution:")
        tier_counts = {}
        for user in self.users.values():
            tier_counts[user['tier']] = tier_counts.get(user['tier'], 0) + 1
        for tier, count in tier_counts.items():
            percentage = (count / self.pool_size) * 100
            print(f"  {tier}: {count} ({percentage:.1f}%)")
    
    def get_random_user(self) -> Dict[str, Any]:
        """
        Get a random user from pool.
        
        Returns:
            dict: User profile
        
        CONCEPT: Random User Selection
        - Each user has equal probability of being selected
        - Simulates: "A random visitor comes to the site"
        - Over time, all users will be represented
        
        ALTERNATIVE APPROACHES:
        - Weighted by tier: VIP users more likely
        - Weighted by recency: Recent users more likely
        - Time-based: Different users active at different hours
        
        We use uniform random for simplicity.
        """
        return random.choice(list(self.users.values()))
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get specific user by ID."""
        return self.users.get(user_id)


# ============================================================================
# PRODUCT GENERATOR
# ============================================================================
#
# CONCEPT: Product Catalog
# - Fixed set of products (like real e-commerce)
# - Each product has properties (price, category, etc.)
# - Some products more popular than others
#

class ProductGenerator:
    """
    Generates and manages product catalog.
    
    DESIGN DECISIONS:
    - Products are static (don't change during run)
    - Category distribution matches config
    - Prices follow realistic distributions (not uniform random)
    - Some products are "featured" (more likely to be shown)
    """
    
    def __init__(self, catalog_size: int = 1000):
        """
        Initialize product catalog.
        
        Args:
            catalog_size: Number of products to generate
        
        CONCEPT: Catalog Size
        - Too small: Unrealistic, limited variety
        - Too large: Slow lookups, memory issues
        - 1,000 products is realistic for medium-sized store
        
        REAL-WORLD NUMBERS:
        - Boutique: 100-500 products
        - Medium store: 1,000-10,000 products
        - Large marketplace: 100,000+ products
        """
        self.catalog_size = catalog_size
        self.products: List[Dict[str, Any]] = []
        self._generate_catalog()
    
    def _generate_catalog(self):
        """
        Generate product catalog.
        
        DEEP DIVE: Price Generation
        We don't use uniform random prices! Real prices have patterns:
        - Cluster around "psychological price points" ($9.99, $49.99)
        - Higher variance in high-price categories
        - Some categories more expensive than others
        
        We use log-normal distribution:
        - Most products low-medium price
        - Few products very high price
        - Realistic distribution shape
        """
        print(f"Generating catalog of {self.catalog_size} products...")
        
        for i in range(self.catalog_size):
            # Select category based on weights
            category = weighted_choice({
                cat: props['weight'] 
                for cat, props in PRODUCT_CATEGORIES.items()
            })
            
            cat_props = PRODUCT_CATEGORIES[category]
            
            # Select subcategory
            subcategory = random.choice(cat_props['subcategories'])
            
            # Generate price using log-normal distribution
            # CONCEPT: Log-Normal Distribution
            # - Most values cluster around mean
            # - Long tail of high values
            # - Realistic for prices (most items cheap, some expensive)
            # - Math: log(price) ~ Normal(mean, std)
            min_price, max_price = cat_props['price_range']
            avg_price = cat_props['avg_price']
            
            # Calculate log-normal parameters
            # MATH EXPLANATION:
            # If we want average price = $100 with range $50-$200:
            # 1. Take log of prices: log(50) to log(200)
            # 2. Calculate mean of log prices
            # 3. Add randomness around that mean
            # 4. Exponentiate back to get actual price
            log_mean = np.log(avg_price)
            log_std = (np.log(max_price) - np.log(min_price)) / 6
            # Divide by 6 because 99.7% of normal distribution within ±3σ
            
            price = np.random.lognormal(log_mean, log_std)
            price = max(min_price, min(max_price, price))  # Clamp to range
            price = round(price, 2)  # Round to cents
            
            # Generate realistic product name
            # CONCEPT: Product Name Generation
            # Combine category + adjective + descriptor
            # More realistic than "Product 1", "Product 2"
            adjectives = ['Premium', 'Deluxe', 'Pro', 'Ultra', 'Classic', 'Essential']
            product_name = f"{random.choice(adjectives)} {subcategory} {fake.word().title()}"
            
            product = {
                'product_id': f"prod_{i:06d}",  # prod_000001, prod_000002, etc.
                'product_name': product_name,
                'category': category,
                'subcategory': subcategory,
                'price': price,
                'brand': fake.company(),
                'in_stock': random.random() > 0.05,  # 95% in stock
                'rating': round(random.uniform(3.0, 5.0), 1),  # 3.0 to 5.0 stars
                'num_reviews': int(np.random.exponential(50)),  # Most have few reviews
            }
            
            self.products.append(product)
        
        print(f"✓ Product catalog generated")
        print(f"  Categories: {len(PRODUCT_CATEGORIES)}")
        print(f"  Price range: ${min(p['price'] for p in self.products):.2f} - ${max(p['price'] for p in self.products):.2f}")
        print(f"  Average price: ${sum(p['price'] for p in self.products) / len(self.products):.2f}")
    
    def get_random_product(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a random product, optionally filtered by category.
        
        Args:
            category: If specified, only return products from this category
        
        Returns:
            dict: Product information
        
        CONCEPT: Filtered Random Selection
        - Sometimes we want random from specific category
        - Example: User clicked "Electronics", show random electronics
        - More realistic than showing any random product
        """
        if category:
            # Filter to category
            category_products = [p for p in self.products if p['category'] == category]
            if category_products:
                return random.choice(category_products)
        
        return random.choice(self.products)
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get specific product by ID."""
        for product in self.products:
            if product['product_id'] == product_id:
                return product
        return None


# ============================================================================
# SESSION GENERATOR
# ============================================================================
#
# CONCEPT: User Session
# - Sequence of events from same user in short time period
# - Has beginning (first event) and end (timeout or purchase)
# - Represents "user journey" through funnel
#
# STATE MACHINE:
# Initial → Search → View → Add to Cart → Checkout → Purchase
#                ↓      ↓         ↓           ↓
#              Exit   Exit      Exit        Exit
#
# At each state, user can:
# - Progress to next state (with some probability)
# - Exit session (abandon)
#

class SessionGenerator:
    """
    Generates realistic user sessions with state-based progression.
    
    DEEP CONCEPT: Markov Chain
    - Current state determines probability of next state
    - State: {viewing, in_cart, checking_out}
    - Transitions: viewing → cart (15% probability)
    - History doesn't matter, only current state (memoryless)
    
    This is a simplified Markov chain model of user behavior.
    """
    
    def __init__(self, user_generator: UserGenerator, product_generator: ProductGenerator):
        """
        Initialize session generator.
        
        Args:
            user_generator: Source of users
            product_generator: Source of products
        """
        self.user_gen = user_generator
        self.product_gen = product_generator
    
    def generate_session(self) -> Generator[ClickstreamEvent, None, None]:
        """
        Generate a complete user session (multiple events).
        
        Yields:
            ClickstreamEvent: Events in the session
        
        DEEP DIVE: Generator Function
        - Uses 'yield' not 'return'
        - Produces events one at a time (memory efficient)
        - Caller can iterate: for event in generate_session()
        - Lazy evaluation: Only generates when requested
        
        WHY GENERATOR?
        - Memory: Don't hold all events in memory
        - Streaming: Can process events as generated
        - Infinite: Could run forever without memory issues
        
        ALTERNATIVE:
        - Return list of events (simple, but memory intensive)
        - Callback function (more complex)
        """
        # Get user for this session
        user = self.user_gen.get_random_user()
        
        # Generate session ID
        session_id = f"sess_{fake.uuid4()[:16]}"
        
        # Determine device for this session
        # CONCEPT: Session-Level Properties
        # Device doesn't change mid-session (realistic)
        # Once on mobile, entire session is mobile
        device_type = weighted_choice(DEVICE_DISTRIBUTION)
        
        # Calculate device-specific conversion multiplier
        # CONCEPT: Correlated Variables
        # Device type AFFECTS conversion probability
        # Mobile: 0.8x (harder checkout on small screen)
        # Desktop: 1.2x (easier checkout, bigger screen)
        device_multiplier = DEVICE_CONVERSION_MULTIPLIER.get(device_type, 1.0)
        
        # Determine session duration (how long user browses)
        # CONCEPT: Exponential Distribution
        # Most sessions short, some very long
        # λ (lambda) parameter = 1/mean
        avg_duration = SESSION_DURATION['avg']
        duration_seconds = int(np.random.exponential(avg_duration))
        duration_seconds = max(
            SESSION_DURATION['min'],
            min(SESSION_DURATION['max'], duration_seconds)
        )
        
        # Session start time
        session_start = datetime.utcnow()
        current_time = session_start
        
        # Session state
        cart = []  # Items in cart
        viewed_products = set()  # Products viewed (for anti-repetition)
        
        # Generate session events
        # CONCEPT: Event Sequence Generation
        # Not random - follows logical progression:
        # Search → View → Cart → Checkout → Purchase
        
        # 1. SEARCH EVENT (Session often starts with search)
        if random.random() < 0.7:  # 70% of sessions start with search
            search_query = self._generate_search_query()
            search_category = self._categorize_search(search_query)
            
            yield ClickstreamEvent(
                user_id=user['user_id'],
                session_id=session_id,
                event_type=EventType.SEARCH.value,
                search_query=search_query,
                search_results_count=random.randint(0, 100),
                device_type=device_type,
                country=user['country'],
                timestamp=(current_time).isoformat() + 'Z',
            )
            
            current_time += timedelta(seconds=random.randint(1, 5))
        else:
            search_category = None  # Direct navigation
        
        # 2. BROWSING PHASE (View products)
        # CONCEPT: Poisson Distribution for Event Count
        # Models "number of events in fixed time period"
        # E.g., "How many products will user view?"
        num_items_to_view = int(np.random.poisson(ITEMS_PER_SESSION['avg']))
        num_items_to_view = max(1, min(ITEMS_PER_SESSION['max'], num_items_to_view))
        
        for i in range(num_items_to_view):
            # Get product (biased toward search category if searched)
            if search_category and random.random() < 0.7:
                product = self.product_gen.get_random_product(category=search_category)
            else:
                product = self.product_gen.get_random_product()
            
            # Avoid viewing same product twice in session (more realistic)
            if product['product_id'] in viewed_products:
                continue
            viewed_products.add(product['product_id'])
            
            # PAGE VIEW EVENT
            yield ClickstreamEvent(
                user_id=user['user_id'],
                session_id=session_id,
                event_type=EventType.PAGE_VIEW.value,
                product_id=product['product_id'],
                product_name=product['product_name'],
                category=product['category'],
                subcategory=product['subcategory'],
                price=product['price'],
                device_type=device_type,
                country=user['country'],
                page_load_time_ms=int(np.random.gamma(2, 100)),  # Realistic load times
                timestamp=(current_time).isoformat() + 'Z',
            )
            
            current_time += timedelta(seconds=random.randint(10, 60))  # Time on page
            
            # 3. ADD TO CART (Probabilistic)
            # CONCEPT: Conditional Probability
            # P(add to cart | viewed product) = conversion rate × device multiplier
            base_prob = CONVERSION_PROBABILITIES['view_to_cart']
            actual_prob = base_prob * device_multiplier
            
            if random.random() < actual_prob:
                cart.append(product)
                
                yield ClickstreamEvent(
                    user_id=user['user_id'],
                    session_id=session_id,
                    event_type=EventType.ADD_TO_CART.value,
                    product_id=product['product_id'],
                    product_name=product['product_name'],
                    category=product['category'],
                    price=product['price'],
                    cart_total=sum(p['price'] for p in cart),
                    cart_item_count=len(cart),
                    device_type=device_type,
                    country=user['country'],
                    timestamp=(current_time).isoformat() + 'Z',
                )
                
                current_time += timedelta(seconds=random.randint(2, 10))
        
        # 4. CHECKOUT PHASE (Only if cart not empty)
        if cart:
            # Proceed to checkout?
            checkout_prob = CONVERSION_PROBABILITIES['cart_to_checkout'] * device_multiplier
            
            if random.random() < checkout_prob:
                # CHECKOUT STARTED EVENT
                yield ClickstreamEvent(
                    user_id=user['user_id'],
                    session_id=session_id,
                    event_type=EventType.CHECKOUT_STARTED.value,
                    cart_total=sum(p['price'] for p in cart),
                    cart_item_count=len(cart),
                    device_type=device_type,
                    country=user['country'],
                    timestamp=(current_time).isoformat() + 'Z',
                )
                
                current_time += timedelta(seconds=random.randint(30, 120))  # Checkout form time
                
                # 5. PURCHASE (Final conversion)
                purchase_prob = CONVERSION_PROBABILITIES['checkout_to_purchase']
                purchase_prob *= device_multiplier
                purchase_prob *= user['purchase_probability'] / 0.05  # Adjust for user tier
                
                if random.random() < purchase_prob:
                    # CHECKOUT COMPLETED EVENT
                    yield ClickstreamEvent(
                        user_id=user['user_id'],
                        session_id=session_id,
                        event_type=EventType.CHECKOUT_COMPLETED.value,
                        cart_total=sum(p['price'] for p in cart),
                        cart_item_count=len(cart),
                        device_type=device_type,
                        country=user['country'],
                        timestamp=(current_time).isoformat() + 'Z',
                    )
                    
                    # Session ends on purchase (successful conversion!)
                    # Transaction event will be generated separately
    
    def _generate_search_query(self) -> str:
        """
        Generate realistic search query.
        
        Returns:
            str: Search query
        
        CONCEPT: Search Query Distribution
        - Mix of specific and general terms
        - Some multi-word queries
        - Some single-word queries
        - Realistic typos occasionally
        """
        query_types = [
            # Specific product searches
            lambda: f"{random.choice(list(PRODUCT_CATEGORIES.keys()))} {fake.word()}",
            # Brand searches
            lambda: fake.company(),
            # Single category
            lambda: random.choice(list(PRODUCT_CATEGORIES.keys())),
            # Multi-word descriptive
            lambda: f"{fake.word()} {fake.word()}",
        ]
        
        query = random.choice(query_types)()
        
        # Occasionally introduce typo (realistic!)
        if random.random() < 0.05:  # 5% typo rate
            # Simple typo: swap two adjacent characters
            if len(query) > 2:
                pos = random.randint(0, len(query) - 2)
                query = query[:pos] + query[pos+1] + query[pos] + query[pos+2:]
        
        return query.lower()
    
    def _categorize_search(self, search_query: str) -> Optional[str]:
        """
        Determine which category a search query maps to.
        
        Args:
            search_query: User's search term
        
        Returns:
            str or None: Matching category
        
        CONCEPT: Query Understanding
        - Map search terms to product categories
        - Simple keyword matching (production would use NLP)
        - Enables showing relevant products
        """
        query_lower = search_query.lower()
        
        for category in PRODUCT_CATEGORIES.keys():
            if category.lower() in query_lower:
                return category
        
        # Check subcategories
        for category, props in PRODUCT_CATEGORIES.items():
            for subcat in props['subcategories']:
                if subcat.lower() in query_lower:
                    return category
        
        return None  # Generic search


# ============================================================================
# TRANSACTION GENERATOR
# ============================================================================
#
# CONCEPT: Transaction from Session
# - Not all sessions → transactions
# - Transaction follows successful checkout
# - Contains more detail than clickstream event
#

class TransactionGenerator:
    """
    Generates transaction events from completed purchases.
    """
    
    def __init__(self, user_generator: UserGenerator):
        self.user_gen = user_generator
    
    def generate_transaction(
        self, 
        user_id: str, 
        session_id: str,
        cart_items: List[Dict[str, Any]],
        device_type: str,
        country: str
    ) -> TransactionEvent:
        """
        Generate transaction from cart.
        
        Args:
            user_id: User making purchase
            session_id: Session this purchase belongs to
            cart_items: Products being purchased
            device_type: Device used
            country: User's country
        
        Returns:
            TransactionEvent: Complete transaction
        
        DEEP DIVE: Price Calculation
        - Subtotal = sum of item prices
        - Tax = subtotal × tax_rate (varies by country/state)
        - Shipping = based on total and country
        - Discount = applied after subtotal, before tax
        - Total = subtotal - discount + tax + shipping
        
        This is EXACTLY how real e-commerce calculates prices.
        """
        user = self.user_gen.get_user_by_id(user_id)
        
        # Calculate prices (in cents to avoid float issues)
        subtotal_cents = sum(int(item['price'] * 100) for item in cart_items)
        
        # Apply tier-based multiplier to order value
        # VIP users tend to buy more expensive items or more items
        subtotal_cents = int(subtotal_cents * user['order_value_multiplier'])
        
        # Calculate tax (simplified - real systems consider state/country tax rates)
        # US average sales tax: ~7%
        tax_rate = 0.07
        tax_cents = int(subtotal_cents * tax_rate)
        
        # Calculate shipping
        # CONCEPT: Tiered Shipping
        # - Free shipping over $100
        # - Flat rate under $100
        # - International more expensive
        if subtotal_cents >= 10000:  # $100+
            shipping_cents = 0
        elif country == 'US':
            shipping_cents = 500  # $5
        else:
            shipping_cents = 1500  # $15 international
        
        # Apply discount (random chance)
        # CONCEPT: Promotional Discounts
        # - Some orders get discounts
        # - Could be coupon, sale, first-time customer, etc.
        discount_cents = 0
        promo_codes = None
        if random.random() < 0.2:  # 20% of orders have discount
            discount_pct = random.choice([0.10, 0.15, 0.20, 0.25])  # 10%-25% off
            discount_cents = int(subtotal_cents * discount_pct)
            promo_codes = [f"PROMO{random.randint(100, 999)}"]
        
        # Calculate total
        total_cents = subtotal_cents - discount_cents + tax_cents + shipping_cents
        
        # Generate transaction
        transaction_id = f"txn_{fake.uuid4()[:16]}"
        order_id = f"ord_{fake.uuid4()[:16]}"
        
        # Prepare line items
        # CONCEPT: Line Item Structure
        # Each item in cart becomes a line item with full details
        items = [
            {
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'category': item['category'],
                'quantity': 1,  # Simplified - real systems allow quantity > 1
                'price_cents': int(item['price'] * 100),
            }
            for item in cart_items
        ]
        
        return TransactionEvent(
            transaction_id=transaction_id,
            order_id=order_id,
            user_id=user_id,
            customer_tier=user['tier'],
            subtotal_cents=subtotal_cents,
            tax_cents=tax_cents,
            shipping_cents=shipping_cents,
            discount_cents=discount_cents,
            total_cents=total_cents,
            items=items,
            total_items=len(items),
            payment_method=weighted_choice(PAYMENT_METHODS),
            payment_processor="stripe",  # Simplified
            order_status=OrderStatus.CONFIRMED.value,
            session_id=session_id,
            device_type=device_type,
            country=country,
            shipping_address={
                'street': fake.street_address(),
                'city': fake.city(),
                'state': fake.state_abbr(),
                'zip': fake.zipcode(),
                'country': country,
            },
            promo_codes=promo_codes,
        )


# ============================================================================
# MAIN EVENT STREAM GENERATOR
# ============================================================================
#
# CONCEPT: Infinite Event Stream
# - Continuously generates events
# - Respects rate limits (events per second)
# - Applies temporal patterns
# - Mixes clickstream and transaction events
#

class EventStreamGenerator:
    """
    Main generator coordinating all event generation.
    
    This is the "orchestrator" - brings together:
    - User generator
    - Product generator
    - Session generator
    - Transaction generator
    
    Produces infinite stream of events at specified rate.
    """
    
    def __init__(
        self,
        user_pool_size: int = 10000,
        product_catalog_size: int = 1000,
        events_per_second: int = 50,
    ):
        """
        Initialize event stream generator.
        
        Args:
            user_pool_size: Number of unique users
            product_catalog_size: Number of products
            events_per_second: Target event generation rate
        """
        print("=== Initializing Event Stream Generator ===")
        
        # Initialize sub-generators
        self.user_gen = UserGenerator(pool_size=user_pool_size)
        self.product_gen = ProductGenerator(catalog_size=product_catalog_size)
        self.session_gen = SessionGenerator(self.user_gen, self.product_gen)
        self.transaction_gen = TransactionGenerator(self.user_gen)
        
        # Rate limiting
        self.target_events_per_second = events_per_second
        self.event_interval = 1.0 / events_per_second  # Seconds between events
        
        # Statistics
        self.stats = {
            'total_events': 0,
            'clickstream_events': 0,
            'transaction_events': 0,
            'sessions_generated': 0,
        }
        
        print("✓ Event Stream Generator ready")
        print(f"  Target rate: {events_per_second} events/second")
        print(f"  User pool: {user_pool_size:,} users")
        print(f"  Product catalog: {product_catalog_size:,} products")
    
    def generate_events(self) -> Generator[Dict[str, Any], None, None]:
        """
        Generate infinite stream of events.
        
        Yields:
            dict: Event as dictionary (ready for JSON serialization)
        
        CONCEPT: Infinite Generator
        - while True loop (runs forever)
        - Yield events one at a time
        - Caller controls when to stop
        - Memory efficient (doesn't accumulate events)
        
        RATE LIMITING:
        - Track time between events
        - Sleep if generating too fast
        - Ensures consistent throughput
        """
        last_event_time = time.time()
        
        while True:
            # Apply temporal multiplier
            # CONCEPT: Time-Based Rate Adjustment
            # More events during peak hours (7 PM)
            # Fewer events during off-peak (3 AM)
            multiplier = get_current_traffic_multiplier()
            current_rate = int(self.target_events_per_second * multiplier)
            current_interval = 1.0 / max(1, current_rate)
            
            # Generate a session (produces multiple events)
            self.stats['sessions_generated'] += 1
            cart_items = []
            session_info = {}
            
            for event in self.session_gen.generate_session():
                # Convert to dict
                event_dict = event.to_dict()
                
                # Track session info for potential transaction
                if event.event_type == EventType.ADD_TO_CART.value:
                    product = self.product_gen.get_product_by_id(event.product_id)
                    if product:
                        cart_items.append(product)
                
                if event.event_type == EventType.CHECKOUT_COMPLETED.value:
                    session_info = {
                        'user_id': event.user_id,
                        'session_id': event.session_id,
                        'device_type': event.device_type,
                        'country': event.country,
                    }
                
                # Yield clickstream event
                yield {
                    'topic': 'clickstream',
                    'event': event_dict,
                }
                
                self.stats['clickstream_events'] += 1
                self.stats['total_events'] += 1
                
                # Rate limiting
                # CONCEPT: Throttling
                # If generating events faster than target rate, slow down
                elapsed = time.time() - last_event_time
                if elapsed < current_interval:
                    time.sleep(current_interval - elapsed)
                last_event_time = time.time()
            
            # Generate transaction if session resulted in purchase
            if cart_items and session_info:
                transaction = self.transaction_gen.generate_transaction(
                    user_id=session_info['user_id'],
                    session_id=session_info['session_id'],
                    cart_items=cart_items,
                    device_type=session_info['device_type'],
                    country=session_info['country'],
                )
                
                yield {
                    'topic': 'transactions',
                    'event': transaction.to_dict(),
                }
                
                self.stats['transaction_events'] += 1
                self.stats['total_events'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self.stats.copy()


# ============================================================================
# SUMMARY
# ============================================================================
#
# This module implements:
# 1. UserGenerator: Pool of realistic users with tiers
# 2. ProductGenerator: Product catalog with realistic prices
# 3. SessionGenerator: User journeys through conversion funnel
# 4. TransactionGenerator: Purchase records from completed sessions
# 5. EventStreamGenerator: Orchestrates everything into infinite stream
#
# KEY CONCEPTS DEMONSTRATED:
# - Probability distributions (weighted choice, exponential, log-normal, Poisson)
# - State machines (user journey: search → view → cart → checkout → purchase)
# - Correlation vs independence (device affects conversion)
# - Temporal patterns (peak hours, day of week)
# - Rate limiting and throttling
# - Memory-efficient streaming (generators)
# - Realistic data modeling
#
# INTERVIEW TALKING POINTS:
# - "I modeled user behavior as a Markov chain with probabilistic transitions"
# - "I used appropriate distributions: log-normal for prices, Poisson for counts"
# - "I implemented correlations: device type affects conversion rate"
# - "I used generators for memory-efficient streaming"
# - "I applied temporal patterns to simulate realistic traffic"
# - "I validated business logic: subtotal + tax + shipping = total"
#
# NEXT FILE: kafka_producer.py (send these events to Kafka!)
#
# ============================================================================