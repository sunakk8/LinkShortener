from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from . import models, utils, database, schemas
from .redis_client import redis_conn
from .limiter import rate_limiter
from .sync import sync_clicks_to_db
import os

app = FastAPI(title="URL Shortener")

# Initialize the database tables
models.Base.metadata.create_all(bind=database.engine)


@app.get("/")
def read_root():
    return {
        "message": "URL Shortener API is live",
        "salt_check": "Salt is set" if os.getenv("salt") else "Salt is missing"
    }

@app.post("/shorten", response_model=schemas.URLResponse, dependencies=[Depends(rate_limiter)])
def create_short_url(url_request: schemas.URLCreate, db: Session = Depends(database.get_db)):
    # check for custom url
    if url_request.custom_url:
        existing = db.query(models.URL).filter(models.URL.short_code == url_request.custom_url).first()
        if existing:
            raise HTTPException(status_code=400, detail="This URL is already taken. Please try another.")
        
        new_record = models.URL(target_url=url_request.target_url.unicode_string(), 
                                short_code=url_request.custom_url)
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
    else:
        # add new url, get db id
        new_record = models.URL(target_url=url_request.target_url.unicode_string())
        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        # encode db id, update db record
        short_code = utils.encode_id(new_record.id)
        new_record.short_code = short_code
        db.commit()
        db.refresh(new_record)

    # return full short URL
    return schemas.URLResponse(
        short_url=f"http://localhost:8000/{new_record.short_code}",
        target_url= new_record.target_url
    )

@app.get("/{short_code}")
def redirect(short_code: str, db: Session = Depends(database.get_db)):
    # check redis cache first
    cached_url = redis_conn.get(short_code)

    # update metrics
    redis_conn.incr(f"clicks:{short_code}")
    if cached_url:
        return RedirectResponse(url=cached_url)
    
    # miss, query db for url
    db_url = db.query(models.URL).filter(models.URL.short_code == short_code).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # cache for future, 24 hr exp
    redis_conn.setex(short_code, 86400, db_url.target_url)

    return RedirectResponse(url=db_url.target_url)

@app.post("/sync", status_code=202)
def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    background_tasks.add_task(sync_clicks_to_db, db)
    return {"message": "Sync started in background"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}