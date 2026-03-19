import json
import redis


# redis connection string
# booking-redis is the Redis container/service name in docker-compose
# /0 means we are using Redis database 0
# REDIS_URL = "redis://booking-redis:6379/0"
# use service's name instead of contianer's name
REDIS_URL = "redis://redis:6379/0"

# create a Redis client
# decode_responses=True means Redis returns strings instead of bytes
# so we can work with JSON text more easily in Python
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


# build a unique cache key for one inventory item
# example: item_id="iphone" -> "inventory:iphone"
def get_inventory_cache_key(item_id: str) -> str:
    return f"inventory:{item_id}"


def get_cached_inventory(item_id: str):
    # try to read cached inventory data from Redis
    key = get_inventory_cache_key(item_id)
    data = redis_client.get(key)

    # if Redis does not have this key, return None
    # so the caller knows it should fetch from DB/service
    if not data:
        return None
    
    # redis stores strings, so convert JSON string back to Python dict
    return json.loads(data)


def set_cached_inventory(item_id: str, inventory_data: dict):
    # save inventory data into Redis cache
    key = get_inventory_cache_key(item_id)

    # convert Python dict to JSON string before storing
    # ex=300: means this cache expires in 300 seconds (5 minutes)
    redis_client.set(key, json.dumps(inventory_data), ex=300)


def delete_cached_inventory(item_id: str):
    # remove the cached inventory entry from Redis
    # usually used after inventory is updated, so old cached data
    # does not remain stale
    key = get_inventory_cache_key(item_id)
    redis_client.delete(key)