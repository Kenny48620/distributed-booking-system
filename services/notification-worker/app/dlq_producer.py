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

# Kafka producer used to send failed events into a DLQ topic
producer = Producer({
    "bootstrap.servers": "booking-kafka:9092"
})


def dlq_delivery_report(err, msg):
    if err is not None:
        print(f"DLQ delivery failed: {err}")
    else:
        print(
            f"DLQ message delivered to {msg.topic()} "
            f"[partition {msg.partition()}] at offset {msg.offset()}"
        )


def publish_to_dlq(event: dict):
    producer.produce(
        "booking_created_dlq",
        key=str(event["booking_id"]),
        value=json.dumps(event),
        callback=dlq_delivery_report,
    )
    producer.flush()