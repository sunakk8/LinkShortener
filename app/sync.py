# background tasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from . import models, redis_client

def sync_clicks_to_db(db: Session):
    click_keys = redis_client.redis_conn.keys("clicks:*")

    for key in click_keys:
        # key is "clicks:short_code"
        short_code = key.split(":")[1]

        # get count, reset to 0
        count = redis_client.redis_conn.getset(key, 0)

        # update db
        if count and int(count) > 0:
            db.query(models.URL).filter(
                models.URL.short_code == short_code
            ).update({models.URL.clicks: models.URL.clicks + int(count)})
    db.commit()

def cleanup_expired_urls(db: Session):
    now = datetime.now(timezone.utc)
    
    expired_count = db.query(models.URL).filter(
        models.URL.expires_at != None,
        models.URL.expires_at < now
    ).count()

    if expired_count > 0:
        # Delete
        db.query(models.URL).filter(
            models.URL.expires_at != None,
            models.URL.expires_at < now
        ).delete(synchronize_session=False)
        
        db.commit()
        print(f"[{now}] Deleted {expired_count} expired links from Postgres.")
    else:
        print(f"[{now}] No expired links found.")