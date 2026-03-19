import json
from confluent_kafka import Consumer, KafkaError

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

        # Debug: print the full event for debugging / visibility
        print(f"Received booking event: {event}", flush=True)

        # simulate sending a notification to the user
        # in a real system, this could be email, SMS, or push notification
        print(
            f"Simulated notification: booking {event['booking_id']} "
            f"confirmed for user {event['user_id']}",
            flush=True,
        )

# handle manual stop (ctrl+c) gracefully
except KeyboardInterrupt:
    print("Stopping notification worker...", flush=True)

# always close the consumer properly
# so Kafka can clean up resources and commit offsets if needed
finally:
    consumer.close()