'''
    Commands to manually create dlq topic in Kafka
    docker exec -it booking-kafka /opt/kafka/bin/kafka-topics.sh \
                --create \
                --topic booking_created_dlq \
                --bootstrap-server localhost:9092 \
                --partitions 1 \
                --replication-factor 1

    then check it with
    docker exec -it booking-kafka /opt/kafka/bin/kafka-topics.sh \
                --list \
                --bootstrap-server localhost:9092
'''
import json
from confluent_kafka import Producer
from logger import log_info, log_error, log_warning

# Kafka producer used to send failed events into a DLQ topic
producer = Producer({
    "bootstrap.servers": "booking-kafka:9092"
})


def dlq_delivery_report(err, msg):
    if err is not None:
        # print(f"DLQ delivery failed: {err}")
        log_error(
            service="notification-worker",
            component="dlq-producer",
            event="kafka_delivery_failed",
            error=str(err),
        )
    else:
        # print(
        #     f"DLQ message delivered to {msg.topic()} "
        #     f"[partition {msg.partition()}] at offset {msg.offset()}"
        # )
        log_info(
            service="notification-worker",
            component="dlq-producer",
            event="kafka_delivery_succeeded",
            kafka_topic=msg.topic(),
            kafka_partition=msg.partition(),
            kafka_offset=msg.offset(),
        )

def publish_to_dlq(event: dict):
    log_warning(
        service="notification-worker",
        component="dlq-producer",
        event="dlq_publish_attempt",
        event_id=event.get("event_id"),
        booking_id=event.get("booking_id"),
        original_event_type=event.get("event_type"),
        target_topic="booking_created_dlq",
    )
    producer.produce(
        "booking_created_dlq",
        key=str(event["booking_id"]),
        value=json.dumps(event),
        callback=dlq_delivery_report,
    )
    producer.flush()