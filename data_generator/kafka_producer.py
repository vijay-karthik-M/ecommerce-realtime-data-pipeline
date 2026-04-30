"""
KAFKA PRODUCER
==============

Sends generated events to Kafka topics.

DEEP CONCEPTS:
1. Producer Patterns (fire-and-forget vs synchronous vs async)
2. Serialization (Python dict → JSON string → bytes)
3. Error Handling & Retries
4. Batching & Compression
5. Partitioning Strategy
6. Idempotency & Exactly-Once Semantics

INTERVIEW GOLD:
"I implemented a Kafka producer with error handling, retries, and monitoring.
I chose async production with callbacks for throughput while maintaining
reliability. I serialize to JSON for human readability during development."
"""

import json
import logging
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import KAFKA_CONFIG, TOPICS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """
    Kafka producer for streaming events.
    
    DESIGN DECISIONS:
    - Async production (callbacks for success/failure)
    - JSON serialization (human-readable, debugging-friendly)
    - Compression enabled (gzip - best ratio for JSON)
    - Idempotent producer (prevents duplicates on retry)
    """
    
    def __init__(self):
        """Initialize Kafka producer with error handling."""
        logger.info("Initializing Kafka producer...")
        
        try:
            self.producer = KafkaProducer(
                **KAFKA_CONFIG,
                
                # SERIALIZATION
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                # CONCEPT: Serialization Pipeline
                # Python dict → JSON string → UTF-8 bytes
                # Why JSON? Human-readable, widely supported, flexible
                # Alternative: Avro (schema registry), Protobuf (compact)
                
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                # CONCEPT: Message Key
                # Used for partitioning (same key → same partition)
                # Ensures ordering within key
                
                # PERFORMANCE
                retry_backoff_ms=100,
                # Wait 100ms between retries (exponential backoff)
                
                linger_ms=10,
                # CONCEPT: Batching
                # Wait up to 10ms to batch more messages
                # Trade latency for throughput
                # 0 = send immediately, 100+ = aggressive batching
                
                batch_size=16384,  # 16KB
                # Max batch size in bytes
                
                buffer_memory=33554432,  # 32MB
                # Total memory for buffering
                
                enable_idempotence=True,
                # CONCEPT: Idempotent Producer
                # Prevents duplicates even with retries
                # Kafka assigns sequence numbers to detect duplicates
                # Required for exactly-once semantics
            )
            
            logger.info("✓ Kafka producer initialized successfully")
            logger.info(f"  Bootstrap servers: {KAFKA_CONFIG['bootstrap_servers']}")
            logger.info(f"  Compression: {KAFKA_CONFIG['compression_type']}")
            logger.info(f"  Idempotence: enabled")
            
            # Statistics
            self.stats = {
                'sent': 0,
                'failed': 0,
                'retries': 0,
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def send_event(
        self, 
        topic: str, 
        event: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Send event to Kafka topic.
        
        Args:
            topic: Kafka topic name
            event: Event dictionary
            key: Optional partition key
        
        Returns:
            bool: True if sent successfully
        
        CONCEPT: Async Production with Callbacks
        - send() returns immediately (non-blocking)
        - Kafka client handles actual sending in background
        - Callback fired on success/failure
        - Allows high throughput without blocking
        
        ALTERNATIVE PATTERNS:
        1. Fire-and-forget: send() without callback (fast, risky)
        2. Synchronous: future.get() blocks until ack (slow, reliable)
        3. Async with callback: Best balance (this approach)
        """
        try:
            # Get topic name from config
            topic_name = TOPICS.get(topic, topic)
            
            # Use user_id or transaction_id as partition key
            # CONCEPT: Partitioning Strategy
            # - Same user → same partition → ordering preserved
            # - Distributes load across partitions
            # - Enables parallel processing
            if not key:
                key = event.get('user_id') or event.get('transaction_id')
            
            # Send to Kafka (async)
            future = self.producer.send(
                topic_name,
                value=event,
                key=key,
            )
            
            # Add callback for success/failure
            # CONCEPT: Callback Pattern
            # Python equivalent of JavaScript promises
            # then() → on_send_success
            # catch() → on_send_error
            future.add_callback(self._on_send_success, event, topic_name)
            future.add_errback(self._on_send_error, event, topic_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending event to {topic}: {e}")
            self.stats['failed'] += 1
            return False
    
    def _on_send_success(self, record_metadata, event, topic):
        """
        Callback for successful send.
        
        Args:
            record_metadata: Kafka RecordMetadata object
            event: Original event
            topic: Topic name
        
        CONCEPT: RecordMetadata
        Contains information about where message was stored:
        - topic: Which topic
        - partition: Which partition (0-N)
        - offset: Position in partition (unique, monotonic)
        - timestamp: When Kafka received it
        
        This is your "receipt" - proves message was persisted.
        """
        self.stats['sent'] += 1
        
        # Log every 100th event (avoid log spam)
        if self.stats['sent'] % 100 == 0:
            # Handle both dict and object formats for record_metadata
            if isinstance(record_metadata, dict):
                partition = record_metadata.get('partition', '?')
                offset = record_metadata.get('offset', '?')
            else:
                partition = record_metadata.partition
                offset = record_metadata.offset
                
            logger.info(
                f"Sent {self.stats['sent']} events | "
                f"Latest: {topic} partition={partition} "
                f"offset={offset}"
            )
    
    def _on_send_error(self, exc, event, topic):
        """
        Callback for send failure.
        
        Args:
            exc: Exception that occurred
            event: Original event
            topic: Topic name
        
        CONCEPT: Error Types in Kafka
        1. Retriable: Network blip, broker restart (retry works)
        2. Non-retriable: Invalid config, topic doesn't exist (retry fails)
        
        Kafka client auto-retries retriable errors.
        """
        self.stats['failed'] += 1
        logger.error(f"Failed to send event to {topic}: {exc}")
        logger.debug(f"Failed event: {json.dumps(event, indent=2)}")
        
        # In production, might want to:
        # - Write to dead letter queue
        # - Alert ops team
        # - Store locally for later retry
    
    def flush(self):
        """
        Flush any buffered messages.
        
        CONCEPT: Buffering
        - Producer buffers messages for batching
        - flush() forces immediate send of buffered messages
        - Blocks until all messages sent or timeout
        
        WHEN TO CALL:
        - Before shutdown (don't lose buffered messages)
        - After critical messages (ensure they're sent)
        - End of batch processing
        """
        logger.info("Flushing producer buffer...")
        self.producer.flush(timeout=10)  # Wait up to 10 seconds
        logger.info("✓ Buffer flushed")
    
    def close(self):
        """
        Close producer gracefully.
        
        CONCEPT: Graceful Shutdown
        1. Stop accepting new messages
        2. Flush buffered messages
        3. Close network connections
        4. Release resources
        
        IMPORTANT: Always call this before exit!
        Otherwise buffered messages lost.
        """
        logger.info("Closing Kafka producer...")
        self.flush()
        self.producer.close(timeout=10)
        logger.info("✓ Kafka producer closed")
        
        # Print final stats
        logger.info("=== Final Statistics ===")
        logger.info(f"  Total sent: {self.stats['sent']:,}")
        logger.info(f"  Failed: {self.stats['failed']:,}")
        success_rate = (self.stats['sent'] / max(1, self.stats['sent'] + self.stats['failed'])) * 100
        logger.info(f"  Success rate: {success_rate:.2f}%")
    
    def get_stats(self) -> Dict[str, int]:
        """Get producer statistics."""
        return self.stats.copy()


# ============================================================================
# MONITORING & METRICS
# ============================================================================

class ProducerMetrics:
    """
    Collects and exposes metrics about producer performance.
    
    CONCEPT: Observability
    - Can't improve what you don't measure
    - Metrics → Monitoring → Alerts → Action
    
    METRICS TO TRACK:
    - Throughput (events/sec)
    - Latency (time from generate to Kafka ack)
    - Error rate
    - Batch size
    - Compression ratio
    """
    
    def __init__(self):
        self.metrics = {
            'events_sent_total': 0,
            'events_failed_total': 0,
            'bytes_sent_total': 0,
            'send_latency_ms': [],
        }
    
    def record_send(self, success: bool, bytes_sent: int, latency_ms: float):
        """Record a send operation."""
        if success:
            self.metrics['events_sent_total'] += 1
            self.metrics['bytes_sent_total'] += bytes_sent
        else:
            self.metrics['events_failed_total'] += 1
        
        self.metrics['send_latency_ms'].append(latency_ms)
        
        # Keep only last 1000 latencies (memory management)
        if len(self.metrics['send_latency_ms']) > 1000:
            self.metrics['send_latency_ms'] = self.metrics['send_latency_ms'][-1000:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        latencies = self.metrics['send_latency_ms']
        
        return {
            'events_sent': self.metrics['events_sent_total'],
            'events_failed': self.metrics['events_failed_total'],
            'bytes_sent': self.metrics['bytes_sent_total'],
            'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
            'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            'throughput_mbps': (self.metrics['bytes_sent_total'] / 1_000_000) / 60,  # Rough estimate
        }


# ============================================================================
# SUMMARY
# ============================================================================
#
# This module implements:
# 1. KafkaEventProducer: Async producer with error handling
# 2. Serialization: Python dict → JSON → bytes
# 3. Error callbacks: Success and failure handling
# 4. Graceful shutdown: Flush and close properly
# 5. Statistics: Track sent/failed counts
#
# KEY CONCEPTS:
# - Async production with callbacks (throughput + reliability)
# - Idempotent producer (exactly-once semantics)
# - Batching and compression (performance)
# - Error handling and retries (resilience)
# - Graceful shutdown (data integrity)
#
# INTERVIEW POINTS:
# - "I used async production with callbacks for high throughput"
# - "I enabled idempotence to prevent duplicates on retry"
# - "I implemented proper error handling and graceful shutdown"
# - "I tracked metrics for observability"
# - "I chose JSON for human readability during development"
#
# ============================================================================
