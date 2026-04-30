#!/usr/bin/env python3
"""
QUICK TEST - Day 2 Data Generator
==================================

Quick test to verify everything works before running full generator.

TESTS:
1. Configuration loads
2. Schemas validate
3. Generators create events
4. Events serialize to JSON
5. Kafka connection works

Run this BEFORE running the full generator!
"""

import sys
import json

# Add current directory to Python path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator.config import KAFKA_CONFIG, TOPICS, validate_config
from data_generator.schemas import create_sample_clickstream, create_sample_transaction
from data_generator.generators import UserGenerator, ProductGenerator, SessionGenerator
from data_generator.kafka_producer import KafkaEventProducer


def test_configuration():
    """Test 1: Configuration loads and validates."""
    print("=" * 80)
    print("TEST 1: Configuration")
    print("=" * 80)
    
    try:
        validate_config()
        print("✓ Configuration valid")
        print(f"  Kafka: {KAFKA_CONFIG['bootstrap_servers']}")
        print(f"  Topics: {list(TOPICS.values())}")
        return True
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False


def test_schemas():
    """Test 2: Schemas create and serialize."""
    print("\n" + "=" * 80)
    print("TEST 2: Event Schemas")
    print("=" * 80)
    
    try:
        # Create sample events
        clickstream = create_sample_clickstream()
        transaction = create_sample_transaction()
        
        # Convert to dict
        click_dict = clickstream.to_dict()
        trans_dict = transaction.to_dict()
        
        # Serialize to JSON
        click_json = json.dumps(click_dict, indent=2)
        trans_json = json.dumps(trans_dict, indent=2)
        
        print("✓ Clickstream event created and serialized")
        print(f"  Sample: {click_dict['event_type']} by {click_dict['user_id']}")
        
        print("✓ Transaction event created and serialized")
        print(f"  Sample: {trans_dict['transaction_id']} = ${trans_dict['total_cents']/100:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generators():
    """Test 3: Generators create realistic data."""
    print("\n" + "=" * 80)
    print("TEST 3: Data Generators")
    print("=" * 80)
    
    try:
        # Create small pools for testing
        print("Creating user pool (100 users)...")
        user_gen = UserGenerator(pool_size=100)
        print(f"✓ Generated {len(user_gen.users)} users")
        
        print("\nCreating product catalog (50 products)...")
        product_gen = ProductGenerator(catalog_size=50)
        print(f"✓ Generated {len(product_gen.products)} products")
        
        print("\nGenerating test session...")
        session_gen = SessionGenerator(user_gen, product_gen)
        
        event_count = 0
        for event in session_gen.generate_session():
            event_count += 1
            if event_count == 1:
                print(f"✓ First event: {event.event_type}")
            if event_count >= 5:  # Just test first 5 events
                break
        
        print(f"✓ Generated {event_count} events in session")
        
        return True
    except Exception as e:
        print(f"✗ Generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_kafka_connection():
    """Test 4: Kafka connection works."""
    print("\n" + "=" * 80)
    print("TEST 4: Kafka Connection")
    print("=" * 80)
    
    try:
        print("Connecting to Kafka...")
        producer = KafkaEventProducer()
        
        print("\nSending test event...")
        test_event = {
            'test': True,
            'message': 'Day 2 Test Event',
            'timestamp': '2024-02-07T10:00:00Z',
        }
        
        success = producer.send_event('clickstream', test_event, key='test_key')
        
        if success:
            print("✓ Event queued for sending")
            producer.flush()
            print("✓ Event sent to Kafka")
        else:
            print("✗ Failed to queue event")
            return False
        
        producer.close()
        print("✓ Producer closed gracefully")
        
        return True
    except Exception as e:
        print(f"✗ Kafka connection failed: {e}")
        print("\nTROUBLESHOOTING:")
        print("1. Is Docker running? Check: docker ps")
        print("2. Is Kafka container up? Check: docker compose -f docker/docker-compose.yml ps")
        print("3. Check Kafka logs: docker compose -f docker/docker-compose.yml logs kafka")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "DAY 2 TEST SUITE" + " " * 37 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(("Configuration", test_configuration()))
    results.append(("Schemas", test_schemas()))
    results.append(("Generators", test_generators()))
    results.append(("Kafka Connection", test_kafka_connection()))
    
    # Summary
    print("\n\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 32 + "TEST SUMMARY" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name:.<50} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED! Ready to run data generator! 🎉")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Run the generator: python3 -m data_generator.run_generator")
        print("  2. Watch Kafka topics fill with data")
        print("  3. Day 2 complete!")
        print()
        return 0
    else:
        print("\n" + "=" * 80)
        print("⚠️  SOME TESTS FAILED")
        print("=" * 80)
        print("\nPlease fix failed tests before running the generator.")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())