import json
import threading
import time
from datetime import datetime, timezone

from confluent_kafka import Producer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import OutboxEvent

from .logger import log_info, log_error


# Kafka producer used by the outbox publisher to forward events
# from the local outbox table to the message broker
producer = Producer({
    "bootstrap.servers": "booking-kafka:9092"
})

# Kafka callback for debuging
def delivery_report(err, msg):
    if err is not None:
        # print(f"Outbox delivery failed: {err}", flush=True)
        log_error(
            service="booking-service",
            component="outbox-publisher",
            event="kafka_delivery_failed",
            error=str(err),
        )
    else:
        # print(
        #     f"Outbox event delivered to {msg.topic()} "
        #     f"[partition {msg.partition()}] at offset {msg.offset()}",
        #     flush=True,
        # )
        log_info(
            service="booking-service",
            component="outbox-publisher",
            event="kafka_delivery_succeeded",
            kafka_topic=msg.topic(),
            kafka_partition=msg.partition(),
            kafka_offset=msg.offset(),
        )

# background polling loop that continuously scans the outbox table
# for unsent events and publishes them to Kafka
def run_outbox_publisher():
    # print("Outbox publisher started.", flush=True)
    log_info(
        service="booking-service",
        component="outbox-publisher",
        event="publisher_started",
    )
    while True:
        # opean a db session for each polling cycle
        db: Session = SessionLocal()
        try:
            # read a small batch of pending outbox events in creation order
            # ordering helps preserve event publishing order as much as possible
            pending_events = (
                db.query(OutboxEvent)
                .filter(OutboxEvent.status == "PENDING")
                .order_by(OutboxEvent.id.asc())
                .limit(10)
                .all()
            )
            
            # if there is nothing to publish, sleep briefly to avoid
            # busy-waiting and unnecessary database load
            if not pending_events:
                time.sleep(2)
                continue
            
            # access the records
            for outbox_event in pending_events:
                try:
                    # covert the stored JSON string back into a Python object before sending it to Kafka
                    payload = json.loads(outbox_event.payload)
                    log_info(
                        service="booking-service",
                        component="outbox-publisher",
                        event="outbox_event_publish_attempt",
                        outbox_id=outbox_event.id,
                        event_id=outbox_event.event_id,
                        event_type=outbox_event.event_type,
                        aggregate_type=outbox_event.aggregate_type,
                        aggregate_id=outbox_event.aggregate_id,
                    )


                    # publish the outbox event to Kafka
                    producer.produce(
                        outbox_event.event_type,
                        # aggregate_id is used as the message key 
                        # so related events can consistently map to the same partition
                        key=str(outbox_event.aggregate_id),
                        value=json.dumps(payload),
                        callback=delivery_report,
                    )

                    # force delivery before marking the event as SENT
                    # this keeps the outbox row from being marked successful
                    # before the broker acknowledges the publish
                    producer.flush()

                    # mark the outbox event as successfully published
                    outbox_event.status = "SENT"
                    outbox_event.sent_at = datetime.now(timezone.utc)
                    db.commit()

                    # print(
                    #     f"Outbox event {outbox_event.id} marked as SENT",
                    #     flush=True,
                    # )
                    log_info(
                        service="booking-service",
                        component="outbox-publisher",
                        event="outbox_event_marked_sent",
                        outbox_id=outbox_event.id,
                        event_id=outbox_event.event_id,
                        event_type=outbox_event.event_type,
                        aggregate_id=outbox_event.aggregate_id,
                        outbox_status="SENT",
                    )
                except Exception as e:
                    # roll back the DB transaction so the event remains PENDING
                    # and can be retried in a later polling cycle
                    db.rollback()
                    # print(
                    #     f"Failed to publish outbox event {outbox_event.id}: {e}",
                    #     flush=True,
                    # )
                    log_error(
                        service="booking-service",
                        component="outbox-publisher",
                        event="outbox_event_publish_failed",
                        outbox_id=outbox_event.id,
                        event_id=outbox_event.event_id,
                        event_type=outbox_event.event_type,
                        aggregate_id=outbox_event.aggregate_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

        finally:
            db.close()

# start the outbox publisher in a daemon thread so it runs in the
# background together with the booking service process
def start_outbox_publisher():
    thread = threading.Thread(target=run_outbox_publisher, daemon=True)
    thread.start()