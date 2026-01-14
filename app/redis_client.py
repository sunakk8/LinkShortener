import redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_conn = redis.from_url(REDIS_URL, decode_responses=True)

