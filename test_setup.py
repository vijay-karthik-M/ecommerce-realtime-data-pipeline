#!/usr/bin/env python3
"""
TEST SCRIPT FOR DAY 1 SETUP
============================

This script verifies that all Docker services are running correctly.

WHY THIS SCRIPT?
- Validates environment is set up correctly
- Catches issues early (before writing complex code)
- Good practice: Always test infrastructure before building on it

WHAT IT TESTS:
1. Kafka broker is reachable
2. Can create and list Kafka topics
3. Can produce and consume messages
4. PostgreSQL is reachable
5. Can query database tables
6. Grafana is accessible

INTERVIEW TIP:
When asked "How do you debug infrastructure issues?", mention:
- Systematic testing (test each component individually)
- Health checks (verify services before integration)
- Logging and error handling
"""

import sys
import time

def test_kafka():
    """
    Test Kafka connectivity and basic operations
    
    CONCEPT: Kafka Admin Client
    - Creates topics programmatically
    - Lists existing topics
    - Checks broker health
    """
    print("\n" + "="*80)
    print("TEST 1: KAFKA CONNECTIVITY")
    print("="*80)
    
    try:
        from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
        from kafka.admin import NewTopic
        from kafka.errors import TopicAlreadyExistsError
        
        print("✓ kafka-python library installed")
        
        # Connect to Kafka broker
        print("\n→ Connecting to Kafka at localhost:9092...")
        admin_client = KafkaAdminClient(
            bootstrap_servers='localhost:9092',
            client_id='test_client',
            request_timeout_ms=10000  # 10 second timeout
        )
        print("✓ Connected to Kafka broker")
        
        # List existing topics
        print("\n→ Listing existing topics...")
        topics = admin_client.list_topics()
        print(f"✓ Found {len(topics)} topics: {topics}")
        
        # Create a test topic
        test_topic = 'test-topic'
        print(f"\n→ Creating test topic '{test_topic}'...")
        try:
            topic = NewTopic(
                name=test_topic,
                num_partitions=3,  # 3 partitions for parallelism
                replication_factor=1  # 1 replica (we have 1 broker)
            )
            admin_client.create_topics([topic])
            print(f"✓ Created topic '{test_topic}'")
        except TopicAlreadyExistsError:
            print(f"✓ Topic '{test_topic}' already exists (OK)")
        
        # Produce a test message
        print("\n→ Producing test message...")
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: v.encode('utf-8')
        )
        
        future = producer.send(test_topic, value='Hello from Day 1!')
        result = future.get(timeout=10)  # Wait for send to complete
        print(f"✓ Message sent to partition {result.partition}, offset {result.offset}")
        producer.close()
        
        # Consume the test message
        print("\n→ Consuming test message...")
        consumer = KafkaConsumer(
            test_topic,
            bootstrap_servers='localhost:9092',
            auto_offset_reset='earliest',  # Read from beginning
            consumer_timeout_ms=5000,  # Timeout after 5 seconds
            value_deserializer=lambda m: m.decode('utf-8')
        )
        
        message_count = 0
        for message in consumer:
            message_count += 1
            print(f"✓ Consumed message: '{message.value}' from partition {message.partition}, offset {message.offset}")
            if message_count >= 1:  # Just consume one message for test
                break
        
        consumer.close()
        admin_client.close()
        
        print("\n" + "="*80)
        print("✓✓✓ KAFKA TEST PASSED ✓✓✓")
        print("="*80)
        return True
        
    except ImportError:
        print("✗ kafka-python not installed")
        print("  Install with: pip install kafka-python")
        return False
    except Exception as e:
        print(f"\n✗ KAFKA TEST FAILED")
        print(f"  Error: {str(e)}")
        print(f"  Type: {type(e).__name__}")
        print("\n  TROUBLESHOOTING:")
        print("  1. Is Docker running? Check: docker ps")
        print("  2. Is Kafka container up? Check: docker-compose ps")
        print("  3. Check Kafka logs: docker-compose logs kafka")
        print("  4. Wait 30 seconds for Kafka to fully start")
        return False


def test_postgresql():
    """
    Test PostgreSQL connectivity and database schema
    
    CONCEPT: Database Connection Pooling
    - Reuse connections instead of creating new ones
    - Better performance and resource management
    """
    print("\n" + "="*80)
    print("TEST 2: POSTGRESQL CONNECTIVITY")
    print("="*80)
    
    try:
        import psycopg2
        print("✓ psycopg2 library installed")
        
        # Connect to PostgreSQL
        print("\n→ Connecting to PostgreSQL at localhost:5432...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='analytics',
            user='dataeng',
            password='dataeng123',
            connect_timeout=10
        )
        print("✓ Connected to PostgreSQL")
        
        cursor = conn.cursor()
        
        # Test 1: Check schemas
        print("\n→ Checking schemas...")
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('analytics', 'staging', 'metrics')
            ORDER BY schema_name
        """)
        schemas = cursor.fetchall()
        print(f"✓ Found {len(schemas)} schemas:")
        for schema in schemas:
            print(f"  - {schema[0]}")
        
        # Test 2: Check tables in analytics schema
        print("\n→ Checking tables in 'analytics' schema...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'analytics'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"✓ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - analytics.{table[0]}")
        
        # Test 3: Check date dimension is populated
        print("\n→ Checking date dimension...")
        cursor.execute("SELECT COUNT(*) FROM analytics.dim_date")
        date_count = cursor.fetchone()[0]
        print(f"✓ Date dimension has {date_count} rows")
        
        # Test 4: Sample query
        print("\n→ Running sample query (first 5 dates)...")
        cursor.execute("""
            SELECT date_actual, day_name, is_weekend 
            FROM analytics.dim_date 
            ORDER BY date_actual 
            LIMIT 5
        """)
        dates = cursor.fetchall()
        print("✓ Query results:")
        for date in dates:
            weekend_str = "Weekend" if date[2] else "Weekday"
            print(f"  - {date[0]} ({date[1].strip()}) - {weekend_str}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*80)
        print("✓✓✓ POSTGRESQL TEST PASSED ✓✓✓")
        print("="*80)
        return True
        
    except ImportError:
        print("✗ psycopg2 not installed")
        print("  Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"\n✗ POSTGRESQL TEST FAILED")
        print(f"  Error: {str(e)}")
        print(f"  Type: {type(e).__name__}")
        print("\n  TROUBLESHOOTING:")
        print("  1. Is PostgreSQL container up? Check: docker-compose ps")
        print("  2. Check PostgreSQL logs: docker-compose logs postgres")
        print("  3. Try connecting manually: docker exec -it postgres psql -U dataeng -d analytics")
        return False


def test_grafana():
    """
    Test Grafana web interface accessibility
    
    CONCEPT: HTTP Health Checks
    - Verify service is responding to requests
    - Common practice in microservices
    """
    print("\n" + "="*80)
    print("TEST 3: GRAFANA ACCESSIBILITY")
    print("="*80)
    
    try:
        import requests
        print("✓ requests library installed")
        
        # Check Grafana health endpoint
        print("\n→ Checking Grafana at http://localhost:3000...")
        response = requests.get('http://localhost:3000/api/health', timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ Grafana is healthy")
            print(f"  Database: {health_data.get('database', 'unknown')}")
            print(f"  Version: {health_data.get('version', 'unknown')}")
            
            print("\n→ Testing Grafana UI...")
            ui_response = requests.get('http://localhost:3000', timeout=10)
            if ui_response.status_code == 200:
                print("✓ Grafana UI is accessible at http://localhost:3000")
                print("  Login: admin / admin123")
            else:
                print(f"✗ Grafana UI returned status {ui_response.status_code}")
        else:
            print(f"✗ Grafana health check failed with status {response.status_code}")
            return False
        
        print("\n" + "="*80)
        print("✓✓✓ GRAFANA TEST PASSED ✓✓✓")
        print("="*80)
        return True
        
    except ImportError:
        print("✗ requests library not installed")
        print("  Install with: pip install requests")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to Grafana")
        print("  TROUBLESHOOTING:")
        print("  1. Is Grafana container up? Check: docker-compose ps")
        print("  2. Wait 30 seconds for Grafana to fully start")
        print("  3. Check Grafana logs: docker-compose logs grafana")
        return False
    except Exception as e:
        print(f"\n✗ GRAFANA TEST FAILED")
        print(f"  Error: {str(e)}")
        return False


def main():
    """
    Run all tests and report results
    """
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "DAY 1 INFRASTRUCTURE TEST SUITE" + " "*26 + "║")
    print("╚" + "="*78 + "╝")
    
    print("\nThis script will verify that all Docker services are running correctly.")
    print("If any test fails, follow the troubleshooting steps provided.\n")
    
    # Give user a moment to read
    time.sleep(2)
    
    # Run tests
    results = {
        'Kafka': test_kafka(),
        'PostgreSQL': test_postgresql(),
        'Grafana': test_grafana()
    }
    
    # Summary
    print("\n\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*32 + "TEST SUMMARY" + " "*33 + "║")
    print("╚" + "="*78 + "╝")
    
    for service, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {service:.<40} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED! Your Day 1 setup is complete! 🎉")
        print("="*80)
        print("\nNext steps:")
        print("  1. Open Grafana: http://localhost:3000 (admin/admin123)")
        print("  2. Explore PostgreSQL: docker exec -it postgres psql -U dataeng -d analytics")
        print("  3. Ready for Day 2: Data Generator implementation")
        print("\nYour environment is ready! 🚀")
    else:
        print("\n" + "="*80)
        print("⚠️  SOME TESTS FAILED")
        print("="*80)
        print("\nPlease fix the failed tests before proceeding to Day 2.")
        print("Review the troubleshooting steps above for each failed test.")
        sys.exit(1)


if __name__ == '__main__':
    main()
