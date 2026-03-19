import json
from confluent_kafka import Producer

# responsible for publish event
# "booking-kafka:9092" is the Kafka broker address inside docker-compose network
producer = Producer({
    "bootstrap.servers": "booking-kafka:9092"
    # "bootstrap.servers": "booking-kafka:29092"
})

# call back after Kafka tries to deliver the message
def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(
            f"Message delivered to {msg.topic()} "
            f"[partition {msg.partition()}] at offset {msg.offset()}"
        )

# publish a booking_created event to Kafka after a booking is created
def publish_booking_created_event(booking):
    # create a booking event payload that will be sent to Kafka
    event = {
        "event_type": "booking_created",
        "booking_id": booking.id,
        "user_id": booking.user_id,
        "item_id": booking.item_id,
        "quantity": booking.quantity,
        "status": booking.status,
    }

    # send the event to the booking_created topic
    producer.produce(
        "booking_created",
        key=str(booking.id), # determine which partition it's gonna go to
        value=json.dumps(event), # convert python dic to jason string
        callback=delivery_report,
    )

    # force buffered messages to be sent immediately
    # use it for this small project
    producer.flush()