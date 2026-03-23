import redis

# Redis connection used to track retry counts for failed events
# use service name in compose file
REDIS_URL = "redis://redis:6379/0"
# REDIS_URL = "redis://booking-redis:6379/0"
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# maximum number of persisted retry cycles before sending event to DLQ
MAX_RETRIES = 3

# TTLs to avoid leaving retry metadata in Redis forever
RETRY_COUNT_TTL_SECONDS = 86400       # 24 hours
DLQ_FLAG_TTL_SECONDS = 86400          # 24 hours

# haven't used it
# REQUEUE_FLAG_TTL_SECONDS = 60         # 1 minute


# ---------- retry count ----------

# create a Redis key for storing retry count of a specific event
def get_retry_key(event_id: str) -> str:
    return f"retry_count:{event_id}"

def get_retry_count(event_id: str) -> int:
    # key looks something like "retry_count: event_id_01"
    key = get_retry_key(event_id)
    value = redis_client.get(key)
    return int(value) if value else 0

# increment retry count in Redis after a processing failure
def increment_retry_count(event_id: str) -> int:
    key = get_retry_key(event_id)
    # add 1 retry count
    count = redis_client.incr(key)
    # set a TTL so retry keys do not live forever and clutter Redis
    redis_client.expire(key, 86400)
    return count

# remove retry_count after the event is successfully processed
def clear_retry_count(event_id: str):
    key = get_retry_key(event_id)
    redis_client.delete(key)

# return True if has reached or passed the configured limit
def has_exceeded_retries(event_id: str) -> bool:
    return get_retry_count(event_id) >= MAX_RETRIES



# ---------- DLQ flag ----------

# create the Redis key used to record whether an event has already been sent to the dead-letter queue
def get_dlq_key(event_id: str) -> str:
    return f"dlq_sent:{event_id}"

# check whether this event was already sent to DLQ before, which helps prevent duplicate DLQ publishing
def is_event_sent_to_dlq(event_id: str) -> bool:
    key = get_dlq_key(event_id)
    return redis_client.exists(key) == 1

# mark an event as already published to DLQ
# store a short-lived flag in Redis to avoid repeatedly sending the same poison message to DLQ
def mark_event_sent_to_dlq(event_id: str):
    key = get_dlq_key(event_id)
    redis_client.set(key, "1", ex=86400) # 24 hours
    
def clear_dlq_flag(event_id: str):
    key = get_dlq_key(event_id)
    redis_client.delete(key)



# haven't use it yet, for now just make everything simple
# the purpose is to:
# prevent an event publish retry topic too many times in a short period
# ---------- requeue flag ----------

# def get_requeue_key(event_id: str) -> str:
#     return f"requeued:{event_id}"

# def is_event_requeued(event_id: str) -> bool:
#     key = get_requeue_key(event_id)
#     return redis_client.exists(key) == 1

# def mark_event_requeued(event_id: str):
#     key = get_requeue_key(event_id)
#     # short TTL prevents duplicate requeue spam,
#     # but still allows another requeue later if failures continue
#     redis_client.set(key, "1", ex=REQUEUE_FLAG_TTL_SECONDS)

# def clear_requeue_flag(event_id: str):
#     key = get_requeue_key(event_id)
#     redis_client.delete(key)