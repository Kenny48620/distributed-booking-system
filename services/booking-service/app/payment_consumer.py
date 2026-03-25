import json
import threading
from confluent_kafka import Consumer, KafkaError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Booking
from .inventory_client import release_inventory
'''
    When payment succeed or failed from payment-servie/consumer.py, this consumer will consume the messages
'''

def run_payment_result_consumer():
    # create a Kafka consumer to listen for payment result events
    consumer = Consumer({
        "bootstrap.servers": "booking-kafka:9092",
        "group.id": "booking-service-payment-result-group",
        "auto.offset.reset": "earliest",
    })

    # subscribe to both success and failure payment result topics
    consumer.subscribe(["payment_succeeded", "payment_failed"])

    print("Booking Service payment result consumer started.", flush=True)

    try:
        while True:
            # poll Kafka for a new message every 1 second
            msg = consumer.poll(1.0)

            # no message available yet
            if msg is None:
                continue

            # handle Kafka-level errors
            if msg.error():
                # Ignore end-of-partition events
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Kafka error: {msg.error()}", flush=True)
                continue

            # decode the Kafka message into a Python dictionary
            event = json.loads(msg.value().decode("utf-8"))
            event_type = event["event_type"]
            booking_id = event["booking_id"]

            # open a new database session for handling this event
            db = SessionLocal()
            try:
                # find the record
                booking = db.query(Booking).filter(Booking.id == booking_id).first()
                if not booking:
                    print(f"Booking not found for payment result: {booking_id}", flush=True)
                    continue

                # if payment succeeded, mark the booking as confirmed
                if event_type == "payment_succeeded":
                    booking.status = "CONFIRMED"
                    db.commit()
                    print(f"Booking {booking_id} marked as CONFIRMED", flush=True)

                # if payment failed, mark booking as failed
                # and release the previously reserved inventory
                elif event_type == "payment_failed":
                    booking.status = "FAILED"
                    db.commit()
                    print(f"Booking {booking_id} marked as FAILED", flush=True)

                    # Compensation step:
                    # return reserved inventory back to inventory service
                    release_inventory(booking.item_id, booking.quantity)
                    print(
                        f"Released inventory for booking {booking_id}: "
                        f"{booking.item_id} x {booking.quantity}",
                        flush=True,
                    )

            except Exception as e:
                # Roll back DB changes if anything goes wrong
                db.rollback()
                print(f"Failed to handle payment result for booking {booking_id}: {e}", flush=True)

            finally:
                # Always close the DB session after processing
                db.close()

    except KeyboardInterrupt:
        print("Stopping Booking Service payment result consumer...", flush=True)

    finally:
        # close Kafka consumer before exiting
        consumer.close()


def start_payment_result_consumer():
    # run the payment result consumer in a background daemon thread
    # so it does not block the main FastAPI application (FastAPI occupy main thread)
    thread = threading.Thread(target=run_payment_result_consumer, daemon=True)
    thread.start()