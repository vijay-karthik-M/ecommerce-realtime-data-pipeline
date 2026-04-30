#!/usr/bin/env python3
"""
MAIN DATA GENERATOR RUNNER
==========================

This is the entry point to run the data generator.

USAGE:
    python3 run_generator.py

WHAT IT DOES:
1. Initializes all generators
2. Connects to Kafka
3. Starts infinite event generation
4. Handles Ctrl+C gracefully
5. Shows real-time statistics

INTERVIEW TIP:
"I built a complete data generation system that produces realistic
synthetic events at configurable rates, with proper error handling,
graceful shutdown, and real-time monitoring."
"""

import sys
import signal
import time
from datetime import datetime

from data_generator.generators import EventStreamGenerator
from data_generator.kafka_producer import KafkaEventProducer
from data_generator.config import GENERATION_RATES


class DataGeneratorRunner:
    """Main runner coordinating event generation and Kafka production."""
    
    def __init__(self):
        """Initialize runner."""
        self.running = False
        self.generator = None
        self.producer = None
        
        # Setup signal handlers for graceful shutdown
        # CONCEPT: Signal Handling
        # SIGINT = Ctrl+C
        # SIGTERM = kill command
        # Catch these to shutdown gracefully (flush Kafka buffer)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n\n🛑 Shutdown signal received...")
        self.running = False
    
    def run(self):
        """Main execution loop."""
        print("=" * 80)
        print("E-COMMERCE DATA GENERATOR")
        print("=" * 80)
        print()
        print("This generator produces realistic synthetic e-commerce events")
        print("and streams them to Kafka topics.")
        print()
        print("Press Ctrl+C to stop gracefully")
        print()
        print("=" * 80)
        print()
        
        try:
            # Initialize generator
            print("🔧 Initializing event generator...")
            self.generator = EventStreamGenerator(
                user_pool_size=10000,
                product_catalog_size=1000,
                events_per_second=GENERATION_RATES['clickstream_per_second'],
            )
            print()
            
            # Initialize Kafka producer
            print("🔧 Initializing Kafka producer...")
            self.producer = KafkaEventProducer()
            print()
            
            # Start generation
            print("=" * 80)
            print("🚀 STARTING EVENT GENERATION")
            print("=" * 80)
            print()
            print("Generating events... (Ctrl+C to stop)")
            print()
            
            self.running = True
            start_time = time.time()
            last_stats_time = start_time
            
            # Generate and send events
            for event_data in self.generator.generate_events():
                if not self.running:
                    break
                
                # Send to Kafka
                topic = event_data['topic']
                event = event_data['event']
                
                self.producer.send_event(topic, event)
                
                # Print stats every 10 seconds
                current_time = time.time()
                if current_time - last_stats_time >= 10:
                    self._print_stats(current_time - start_time)
                    last_stats_time = current_time
            
            # Graceful shutdown
            print()
            print("=" * 80)
            print("📊 FINAL STATISTICS")
            print("=" * 80)
            self._print_stats(time.time() - start_time)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Always cleanup
            self._cleanup()
    
    def _print_stats(self, elapsed_seconds):
        """Print current statistics."""
        gen_stats = self.generator.get_stats()
        prod_stats = self.producer.get_stats()
        
        print(f"\n{'─' * 80}")
        print(f"⏱️  Runtime: {elapsed_seconds:.0f} seconds ({elapsed_seconds/60:.1f} minutes)")
        print(f"{'─' * 80}")
        print(f"📈 Generation Stats:")
        print(f"   Sessions: {gen_stats['sessions_generated']:,}")
        print(f"   Clickstream events: {gen_stats['clickstream_events']:,}")
        print(f"   Transactions: {gen_stats['transaction_events']:,}")
        print(f"   Total events: {gen_stats['total_events']:,}")
        print(f"   Rate: {gen_stats['total_events'] / max(1, elapsed_seconds):.1f} events/sec")
        print()
        print(f"📤 Kafka Stats:")
        print(f"   Sent: {prod_stats['sent']:,}")
        print(f"   Failed: {prod_stats['failed']:,}")
        success_rate = (prod_stats['sent'] / max(1, prod_stats['sent'] + prod_stats['failed'])) * 100
        print(f"   Success rate: {success_rate:.2f}%")
        print(f"{'─' * 80}")
    
    def _cleanup(self):
        """Cleanup resources."""
        print()
        print("=" * 80)
        print("🧹 CLEANING UP")
        print("=" * 80)
        
        if self.producer:
            self.producer.close()
        
        print()
        print("✓ Cleanup complete")
        print()
        print("=" * 80)
        print("👋 DATA GENERATOR STOPPED")
        print("=" * 80)


if __name__ == '__main__':
    runner = DataGeneratorRunner()
    runner.run()