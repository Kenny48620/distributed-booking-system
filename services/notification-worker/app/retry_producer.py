import json
from confluent_kafka import Producer

producer = Producer({
    "bootstrap.servers": "booking-kafka:9092",
})


def publish_to_retry_topic(event: dict):
    # publish a failed event to the retry topic for later reprocessing.
    producer.produce(
        "booking_created_retry",
        key=event["event_id"],
        value=json.dumps(event).encode("utf-8"),
    )
    producer.flush()