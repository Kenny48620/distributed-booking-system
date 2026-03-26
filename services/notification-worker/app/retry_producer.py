import json
from confluent_kafka import Producer
from logger import log_info, log_error, log_warning

producer = Producer({
    "bootstrap.servers": "booking-kafka:9092",
})

def retry_delivery_report(err, msg):
    if err is not None:
        log_error(
            service="notification-worker",
            component="retry-producer",
            event="kafka_delivery_failed",
            error=str(err),
        )
    else:
        log_info(
            service="notification-worker",
            component="retry-producer",
            event="kafka_delivery_succeeded",
            kafka_topic=msg.topic(),
            kafka_partition=msg.partition(),
            kafka_offset=msg.offset(),
        )


def publish_to_retry_topic(event: dict):
    # publish a failed event to the retry topic for later reprocessing.
    log_warning(
        service="notification-worker",
        component="retry-producer",
        event="retry_publish_attempt",
        event_id=event.get("event_id"),
        booking_id=event.get("booking_id"),
        original_event_type=event.get("event_type"),
        target_topic="booking_created_retry",
    )
    producer.produce(
        "booking_created_retry",
        key=event["event_id"],
        value=json.dumps(event).encode("utf-8"),
    )
    producer.flush()