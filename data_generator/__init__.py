"""
E-Commerce Data Generator Package
==================================

This package generates realistic synthetic e-commerce data for testing
and development of streaming data pipelines.

WHY A PACKAGE?
- Organized code structure
- Easy imports: `from data_generator import generate_events`
- Can be installed: `pip install -e .`
- Professional standard

USAGE:
    from data_generator.generators import ClickstreamGenerator
    from data_generator.kafka_producer import KafkaEventProducer
    
    generator = ClickstreamGenerator()
    producer = KafkaEventProducer()
    
    for event in generator.generate():
        producer.send(event)

"""

__version__ = '0.1.0'
__author__ = 'Your Name'

# Make key classes easily accessible
# This allows: from data_generator import ClickstreamGenerator
# Instead of: from data_generator.generators import ClickstreamGenerator

# We'll add these imports after creating the modules
# from .generators import ClickstreamGenerator, TransactionGenerator
# from .kafka_producer import KafkaEventProducer
# from .config import KAFKA_CONFIG, TOPICS
