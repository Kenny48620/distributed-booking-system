import json
import uuid
from confluent_kafka import Consumer, Producer, KafkaError

# Kafka consumer used to read payment request events
consumer = Consumer({
    "bootstrap.servers": "booking-kafka:9092",
    # consumer group name
    "group.id": "payment-service-group", 
    # if there is no committed offset yet, start reading from the beginning of the topic
    "auto.offset.reset": "earliest",
})

# Kafka producer used to publish payment result events
producer = Producer({
    "bootstrap.servers": "booking-kafka:9092",
})

# listen for payment requests from the booking service
consumer.subscribe(["payment_requested"])

print("Payment service started. Waiting for payment requests...", flush=True)

# set to True when you want to simulate payment failure
SIMULATE_PAYMENT_FAILURE = False


def delivery_report(err, msg):
    # callback triggered after Kafka attempts to deliver the message
    if err is not None:
        print(f"Payment event delivery failed: {err}", flush=True)
    else:
        print(
            f"Payment event delivered to {msg.topic()} "
            f"[partition {msg.partition()}] at offset {msg.offset()}",
            flush=True,
        )


def publish_payment_succeeded(event: dict):
    # build the success event to notify downstream services
    result_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "payment_succeeded",
        "booking_id": event["booking_id"],
        "user_id": event["user_id"],
        "item_id": event["item_id"],
        "quantity": event["quantity"],
    }

    # publish the payment success event
    producer.produce(
        "payment_succeeded",
        key=str(event["booking_id"]),  # use booking id as the Kafka message key
        value=json.dumps(result_event),  # serialize the event payload to JSON
        callback=delivery_report, # no matter payment success or failed we'll get the report
    )

    # send buffered messages immediately
    producer.flush()


def publish_payment_failed(event: dict):
    # build the failure event to notify downstream services
    result_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "payment_failed",
        "booking_id": event["booking_id"],
        "user_id": event["user_id"],
        "item_id": event["item_id"],
        "quantity": event["quantity"],
    }

    # publish the payment failure event
    producer.produce(
        "payment_failed",
        key=str(event["booking_id"]),  # use booking id as the Kafka message key
        value=json.dumps(result_event),  # serialize the event payload to JSON
        callback=delivery_report,
    )

    # send buffered messages immediately
    producer.flush()


try:
    while True:
        # poll Kafka for the next message
        msg = consumer.poll(1.0)

        # no message received during this poll interval
        if msg is None:
            continue

        # handle Kafka-level consumer errors
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            print(f"Kafka error: {msg.error()}", flush=True)
            continue

        # decode the Kafka message into a Python dict
        event = json.loads(msg.value().decode("utf-8"))
        print(f"Received payment request event: {event}", flush=True)

        # simulate either a success or failure result for this payment request
        if SIMULATE_PAYMENT_FAILURE:
            print(
                f"Simulating payment failure for booking {event['booking_id']}",
                flush=True,
            )
            publish_payment_failed(event)
        else:
            print(
                f"Simulating payment success for booking {event['booking_id']}",
                flush=True,
            )
            publish_payment_succeeded(event)

except KeyboardInterrupt:
    # allow graceful shutdown when the service is stopped manually
    print("Stopping payment service...", flush=True)

finally:
    # close the Kafka consumer cleanly before exit
    consumer.close()
