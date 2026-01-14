# sync clicks metric from cache to db
from sqlalchemy.orm import Session
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