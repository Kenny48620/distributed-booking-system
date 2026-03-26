import json
import uuid
from confluent_kafka import Consumer, Producer, KafkaError
from .logger import log_info, log_error, log_warning
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


# print("Payment service started. Waiting for payment requests...", flush=True)
log_info(
    service="payment-service",
    component="payment-consumer",
    event="consumer_started",
    topics="payment_requested",
)

# set to True when you want to simulate payment failure
SIMULATE_PAYMENT_FAILURE = False


def delivery_report(err, msg):
    # callback triggered after Kafka attempts to deliver the message
    if err is not None:
        # print(f"Payment event delivery failed: {err}", flush=True)
        log_error(
            service="payment-service",
            component="payment-consumer",
            event="kafka_delivery_failed",
            error=str(err),
        )
    else:
        # print(
        #     f"Payment event delivered to {msg.topic()} "
        #     f"[partition {msg.partition()}] at offset {msg.offset()}",
        #     flush=True,
        # )
        log_info(
            service="payment-service",
            component="payment-consumer",
            event="kafka_delivery_succeeded",
            kafka_topic=msg.topic(),
            kafka_partition=msg.partition(),
            kafka_offset=msg.offset(),
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
    log_info(
        service="payment-service",
        component="payment-consumer",
        event="payment_result_publish_attempt",
        result_event_type="payment_succeeded",
        booking_id=event["booking_id"],
    )

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

    log_warning(
        service="payment-service",
        component="payment-consumer",
        event="payment_result_publish_attempt",
        result_event_type="payment_failed",
        booking_id=event["booking_id"],
    )

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
            # print(f"Kafka error: {msg.error()}", flush=True)
            log_error(
                service="payment-service",
                component="payment-consumer",
                event="kafka_consume_error",
                error=str(msg.error()),
            )
            continue

        # decode the Kafka message into a Python dict
        event = json.loads(msg.value().decode("utf-8"))
        # print(f"Received payment request event: {event}", flush=True)
        log_info(
            service="payment-service",
            component="payment-consumer",
            event="payment_request_received",
            event_id=event.get("event_id"),
            booking_id=event["booking_id"],
            user_id=event["user_id"],
            item_id=event["item_id"],
            quantity=event["quantity"],
        )

        # simulate either a success or failure result for this payment request
        if SIMULATE_PAYMENT_FAILURE:
            # print(
            #     f"Simulating payment failure for booking {event['booking_id']}",
            #     flush=True,
            # )
            log_warning(
                service="payment-service",
                component="payment-consumer",
                event="payment_failure_simulated",
                booking_id=event["booking_id"],
            )
            publish_payment_failed(event)
        else:
            # print(
            #     f"Simulating payment success for booking {event['booking_id']}",
            #     flush=True,
            # )
            log_info(
                service="payment-service",
                component="payment-consumer",
                event="payment_success_simulated",
                booking_id=event["booking_id"],
            )
            publish_payment_succeeded(event)

except KeyboardInterrupt:
    # allow graceful shutdown when the service is stopped manually
    # print("Stopping payment service...", flush=True)
    log_info(
        service="payment-service",
        component="payment-consumer",
        event="consumer_stopping",
    )

finally:
    # close the Kafka consumer cleanly before exit
    consumer.close()
