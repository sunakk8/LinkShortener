from fastapi import HTTPException, Request
from .redis_client import redis_conn

RATE_LIMIT = 10
WINDOW_SECONDS = 60

def rate_limiter(request: Request):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"

    # Check if over rate limit
    curr_count = redis_conn.get(key)
    if curr_count and int(curr_count) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. You're being rate limited."
        )
    
    pipe = redis_conn.pipeline()
    pipe.incr(key)
    # if new
    if redis_conn.ttl(key) == -1:
        pipe.expire(key, WINDOW_SECONDS)
    pipe.execute()
