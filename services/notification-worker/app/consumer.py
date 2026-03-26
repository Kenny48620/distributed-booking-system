import json
import time

from confluent_kafka import Consumer, KafkaError
from sqlalchemy.orm import Session
from redis_client import is_event_processed, mark_event_processed

# used to count failures and stop retrying after MAX_RETRIES
from retry_tracker import (
    get_retry_count,
    increment_retry_count,
    clear_retry_count,
    has_exceeded_retries,
    is_event_sent_to_dlq,
    mark_event_sent_to_dlq,
)

from dlq_producer import publish_to_dlq
from retry_producer import publish_to_retry_topic

from database import SessionLocal
from models import Notification
from init_db import init_db
from logger import log_info, log_warning, log_error

# create database tables on startup
init_db()

# cereate a Kafka consumer
# it connects to the Kafka broker inside the docker-compose network
consumer = Consumer({

    "bootstrap.servers": "booking-kafka:9092",
    # consumer group name
    # multiple consumers in the same group can share the workload
    "group.id": "notification-worker-group",
    # if there is no committed offset yet, start reading from the beginning of the topic
    "auto.offset.reset": "earliest",
})

# make the notification worker listen to the "booking_created" topic through this Kafka consumer
consumer.subscribe(["booking_created", "booking_created_retry"])

# print("Notification worker started. Waiting for events...", flush=True)
log_info(
    service="notification-worker",
    component="booking-created-consumer",
    event="consumer_started",
    topics="booking_created,booking_created_retry",
)

# in-memory set to remember which events have already been processed
# this is the simplest idempotency mechanism for now
# for the future use, I'll put the event_ids to Redis and DB
# processed_event_ids = set()


# set this to True only for testing retry behavior
# when enabled, every event processing attempt will fail on purpose
SIMULATE_FAILURE = False

# number of immediate retries inside one processing attempt
MAX_IMMEDIATE_RETRIES = 3

def send_to_dlq_once(event: dict, event_id: str):
    # avoid publishing the same failed event to DLQ more than once
    if is_event_sent_to_dlq(event_id):
        # print(f"Event {event_id} was already sent to DLQ. Skipping duplicate DLQ publish.", flush=True)
        log_warning(
            service="notification-worker",
            component="booking-created-consumer",
            event="dlq_publish_skipped_duplicate",
            event_id=event_id,
        )
        return

    publish_to_dlq(event)
    mark_event_sent_to_dlq(event_id)
    # print(f"Event {event_id} published to DLQ and marked in Redis.", flush=True)
    log_warning(
        service="notification-worker",
        component="booking-created-consumer",
        event="event_sent_to_dlq",
        event_id=event_id,
        original_event_type=event.get("event_type"),
        booking_id=event.get("booking_id"),
    )

# not use yet
# def requeue_once(event: dict, event_id: str):
#     # prevent duplicate retry-topic publishing in a short time window
#     if is_event_requeued(event_id):
#         print(f"Event {event_id} already requeued recently. Skipping duplicate retry publish.", flush=True)
#         return

#     publish_to_retry_topic(event)
#     mark_event_requeued(event_id)
#     print(f"Event {event_id} requeued to retry topic.", flush=True)

try:
    while True:
        # poll Kafka for a message every 1 second
        msg = consumer.poll(1.0)

        # no message received during this poll interval
        if msg is None:
            continue

        # kafka returned an error instead of a normal message
        if msg.error():
            # ignore end of partition marker errors
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            # print other Kafka errors and continue listening
            # print(f"Kafka error: {msg.error()}")
            log_error(
                service="notification-worker",
                component="booking-created-consumer",
                event="kafka_consume_error",
                error=str(msg.error()),
            )
            continue
        
        # decode Kafka message value from bytes -> JSON -> Python dict
        event = json.loads(msg.value().decode("utf-8"))
        event_id = event['event_id']
        topic = msg.topic()
        # print(f"Received event_id: {event_id} from topic: {topic}", flush=True)
        log_info(
            service="notification-worker",
            component="booking-created-consumer",
            event="notification_event_received",
            event_id=event_id,
            event_type=event.get("event_type"),
            booking_id=event.get("booking_id"),
            user_id=event.get("user_id"),
            kafka_topic=topic,
        )

        # if topic == "booking_created_retry":
        #     clear_requeue_flag(event_id)
        #     print(f"Cleared requeue flag for retry-topic event: {event_id}")

        # redis-based idempotency check
        # if we have already successfully processed this event before, skip it to avoid duplicate notifications
        if is_event_processed(event_id):
            # print(f"Duplicate event detected in Redis, skipping: {event_id}", flush=True)
            log_warning(
                service="notification-worker",
                component="booking-created-consumer",
                event="duplicate_event_skipped",
                event_id=event_id,
                booking_id=event.get("booking_id"),
            )
            continue
        
        # read current persisted retry count for observability/logging
        current_retry_count = get_retry_count(event_id)
        # print(f"Current persisted retry count for {event_id}: {current_retry_count}", flush=True)
        log_info(
            service="notification-worker",
            component="booking-created-consumer",
            event="retry_count_loaded",
            event_id=event_id,
            retry_count=current_retry_count,
        )

        # if retry limit already exceeded, send directly to DLQ
        if has_exceeded_retries(event_id):
            # print(f"Max retries exceeded for event {event_id}. Sending to DLQ.", flush=True)
            log_warning(
                service="notification-worker",
                component="booking-created-consumer",
                event="retry_limit_exceeded",
                event_id=event_id,
                retry_count=current_retry_count,
            )
            # publish_to_dlq(event) ## check
            send_to_dlq_once(event, event_id)
            continue
        
        success = False
        # first layer: immediate retry inside same processing cycle
        for attempt in range(1, MAX_IMMEDIATE_RETRIES + 1):
            # open a new database session from SessionLocal
            # this db object is used to talk to PostgreSQL for this event
            db: Session = SessionLocal()
            try:
                # print(f"Immediate attempt {attempt} for event {event_id}")
                log_info(
                    service="notification-worker",
                    component="booking-created-consumer",
                    event="notification_process_attempt_started",
                    event_id=event_id,
                    booking_id=event.get("booking_id"),
                    attempt=attempt,
                )

                # used only for testing failure and retry flow
                if SIMULATE_FAILURE:
                    raise RuntimeError("Simulated notification processing failure")
                
                # create notification message from booking event data
                message = (
                    f"Booking {event['booking_id']} confirmed "
                    f"for user {event['user_id']}"
                )

                # persist notification into PostgreSQL
                # create a class instance for putting into DB
                notification = Notification(
                    event_id=event_id,
                    booking_id=event["booking_id"],
                    user_id=event["user_id"],
                    message=message,
                    status="SENT",
                )
                db.add(notification)
                db.commit()
                db.refresh(notification)

                # print(f"Notification saved to DB: id={notification.id}", flush=True)
                # print(f"Simulated notification: {message}", flush=True)

                log_info(
                    service="notification-worker",
                    component="booking-created-consumer",
                    event="notification_saved",
                    event_id=event_id,
                    booking_id=event.get("booking_id"),
                    notification_id=notification.id,
                    notification_status="SENT",
                )

                # mark event as processed only after DB commit succeeds
                mark_event_processed(event_id)
                # clear retry counter because processing eventually succeeded
                clear_retry_count(event_id)
                # clear_dlq_flag(event_id)

                # print(f"Marked event as processed in Redis: {event_id}", flush=True)
                # print(f"Cleared retry count for event: {event_id}", flush=True)

                log_info(
                    service="notification-worker",
                    component="booking-created-consumer",
                    event="event_marked_processed",
                    event_id=event_id,
                    booking_id=event.get("booking_id"),
                )

                log_info(
                    service="notification-worker",
                    component="booking-created-consumer",
                    event="retry_count_cleared",
                    event_id=event_id,
                )

                success = True
                break

            except Exception as e:
                # roll back any partial DB transaction
                db.rollback()
                # print(f"Immediate attempt {attempt} failed for event {event_id}: {e}", flush=True)

                log_error(
                    service="notification-worker",
                    component="booking-created-consumer",
                    event="notification_process_attempt_failed",
                    event_id=event_id,
                    booking_id=event.get("booking_id"),
                    attempt=attempt,
                    error=str(e),
                    error_type=type(e).__name__,
                )

                # brief delay before next immediate retry
                if attempt < MAX_IMMEDIATE_RETRIES:
                    time.sleep(1)

                # increase retry count so future attempts can be limited
                # retry_count = increment_retry_count(event_id)

                # print(f"Failed to process notification event: {e}", flush=True)
                # print(f"Incremented retry count for {event_id} to {retry_count}", flush=True)

            finally:
                db.close()

        # second layer: if all immediate retries fail, persist retry count
        if not success:
            new_retry_count = increment_retry_count(event_id)
            # print(
            #     f"All immediate retries failed for event {event_id}. "
            #     f"Persisted retry count is now {new_retry_count}"
            # )
            log_warning(
                service="notification-worker",
                component="booking-created-consumer",
                event="immediate_retries_exhausted",
                event_id=event_id,
                booking_id=event.get("booking_id"),
                persisted_retry_count=new_retry_count,
            )
            # if retry count exceeded, send to DLQ
            if has_exceeded_retries(event_id):
                # print(f"Event {event_id} exceeded max retry count. Sending to DLQ.", flush=True)
                log_warning(
                    service="notification-worker",
                    component="booking-created-consumer",
                    event="event_routed_to_dlq",
                    event_id=event_id,
                    booking_id=event.get("booking_id"),
                    persisted_retry_count=new_retry_count,
                )
                send_to_dlq_once(event, event_id)
            else:
                # otherwise publish once to retry topic
                # print(f"Event {event_id} has not exceeded retry limit. Requeueing.", flush=True)
                log_warning(
                    service="notification-worker",
                    component="booking-created-consumer",
                    event="event_requeued_to_retry_topic",
                    event_id=event_id,
                    booking_id=event.get("booking_id"),
                    persisted_retry_count=new_retry_count,
                )
                # requeue flag is intentionally omitted here to keep retry flow simple.
                # persisted retry_count still bounds the total number of retry cycles.
                publish_to_retry_topic(event)

        '''
        Before doing Notification: 

        # Debug: print the full event for debugging / visibility
        print(f"Received booking event: {event}", flush=True)

        # simulate sending a notification to the user
        # in a real system, this could be email, SMS, or push notification
        print(
            f"Simulated notification: booking {event['booking_id']} "
            f"confirmed for user {event['user_id']}",
            flush=True,
        )

        # only mark as processed after side effect succeeds
        mark_event_processed(event_id)
        print(f"Marked event as processed in Redis: {event_id}", flush=True)
        '''

# handle manual stop (ctrl+c) gracefully
except KeyboardInterrupt:
    # print("Stopping notification worker...", flush=True)
    log_info(
        service="notification-worker",
        component="booking-created-consumer",
        event="consumer_stopping",
    )

# always close the consumer properly
# so Kafka can clean up resources and commit offsets if needed
finally:
    consumer.close()
