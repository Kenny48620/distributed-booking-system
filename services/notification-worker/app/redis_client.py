import redis

# connect to Redis container through Docker Compose service name
REDIS_URL = "redis://redis:6379/0"
# REDIS_URL = "redis://booking-redis:6379/0"

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def get_processed_event_key(event_id: str) -> str:
    # each processed event will be stored under a dedicated Redis key
    # ex: booking-created: event_id_01
    return f"processed_event:{event_id}"


def is_event_processed(event_id: str) -> bool:
    # check whether this event id already exists in Redis
    key = get_processed_event_key(event_id)
    return redis_client.exists(key) == 1


def mark_event_processed(event_id: str):
    # mark this event as processed
    # ex=86400 means keep the key for 1 day
    key = get_processed_event_key(event_id)
    redis_client.set(key, "1", ex=86400)