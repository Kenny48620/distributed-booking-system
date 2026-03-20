import json
from confluent_kafka import Consumer, KafkaError
from redis_client import is_event_processed, mark_event_processed

# cereate a Kafka comsumer
# it connects to the Kafka broker inside the docker-compose network
consumer = Consumer({

    "bootstrap.servers": "booking-kafka:9092",
    # "bootstrap.servers": "booking-kafka:29092",

    # consumer group name
    # multiple consumers in the same group can share the workload
    "group.id": "notification-worker-group",

    # if there is no committed offset yet, start reading from the beginning of the topic
    "auto.offset.reset": "earliest",
})

# make the notification worker listen to the "booking_created" topic through this Kafka consumer
consumer.subscribe(["booking_created"])

print("Notification worker started. Waiting for events...", flush=True)

# in-memory set to remember which events have already been processed
# this is the simplest idempotency mechanism for now
# for the future use, I'll put the event_ids to Redis and DB
# processed_event_ids = set()


try:
    while True:
        # poll Kafka for a message
        # wait up to 1 second before returning
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
            print(f"Kafka error: {msg.error()}")
            continue
        
        # decode the message value from bytes to string
        # then parse the JSON payload into a Python dictionary
        event = json.loads(msg.value().decode("utf-8"))
        event_id = event['event_id']
        
        print(f"Processing event_id: {event_id}", flush=True)

        # TEMPORARY SOLUTION FOR 'idempotency check'
        # idempotency check: if we already processed this event_id, skip it
        # this can prevent re-notify actions
        # if event_id in processed_event_ids:
        #     print(f"Duplicate event detected, skipping: {event_id}")
        #     continue
        # # otherwise, we mark the event_id
        # processed_event_ids.add(event_id)


        # redis-based idempotency check (I use event_id to check it if it works as expected)
        # if we've process this event before, stop sending the notification twice
        if is_event_processed(event_id):
            print(f"Duplicate event detected in Redis, skipping: {event_id}")
            continue

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

# handle manual stop (ctrl+c) gracefully
except KeyboardInterrupt:
    print("Stopping notification worker...", flush=True)

# always close the consumer properly
# so Kafka can clean up resources and commit offsets if needed
finally:
    consumer.close()