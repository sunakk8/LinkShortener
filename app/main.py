from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from . import models, utils, database, schemas
from .redis_client import redis_conn
from .limiter import rate_limiter
from .sync import sync_clicks_to_db
from datetime import datetime, timedelta
import json
import os


app = FastAPI(title="URL Shortener")

# Setup templates and static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Initialize the database tables
models.Base.metadata.create_all(bind=database.engine)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/shorten", response_model=schemas.URLResponse, dependencies=[Depends(rate_limiter)])
def create_short_url(url_request: schemas.URLCreate, db: Session = Depends(database.get_db)):
    
    new_record = models.URL(target_url=url_request.target_url.unicode_string())
    expires_at = None
    if url_request.expiry_days:
        expires_at = datetime.utcnow() + timedelta(days=url_request.expiry_days)
    new_record.expires_at = expires_at

    # check for custom url
    if url_request.custom_url:
        existing = db.query(models.URL).filter(models.URL.short_code == url_request.custom_url).first()
        if existing:
            raise HTTPException(status_code=400, detail="This URL is already taken. Please try another.")
        
        new_record.short_code=url_request.custom_url
        db.add(new_record)
        
    else:
        # add new url, get db id
        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        # encode db id, update db record
        new_record.short_code = utils.encode_id(new_record.id)
    db.commit()
    db.refresh(new_record)

    # return full short URL
    return schemas.URLResponse(
        short_url=f"http://localhost:8000/{new_record.short_code}",
        target_url= new_record.target_url
    )

@app.get("/{short_code}")
def redirect(short_code: str, db: Session = Depends(database.get_db)):
    # check Redis first
    cached_data = redis_conn.get(f"url:{short_code}")
    
    if cached_data:
        data = json.loads(cached_data)
        target_url = data["target_url"]
        expires_at_str = data["expires_at"]
        
        # Check expiration
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at < datetime.utcnow():
                raise HTTPException(status_code=410, detail="Sorry, the URL has expired.")
    
    # miss, check db
    else:
        db_url = db.query(models.URL).filter(models.URL.short_code == short_code).first()
        
        if not db_url:
            raise HTTPException(status_code=404, detail="Link not found")

        # Check expiration
        if db_url.expires_at and db_url.expires_at < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Link expired")
        
        target_url = db_url.target_url
        
        # Update Redis
        cache_payload = {
            "target_url": target_url,
            "expires_at": db_url.expires_at.isoformat() if db_url.expires_at else None
        }
        redis_conn.setex(f"url:{short_code}", 86400, json.dumps(cache_payload))

    # Increment click counter in Redis
    redis_conn.incr(f"clicks:{short_code}")

    return RedirectResponse(url=target_url)

@app.post("/sync", status_code=202)
def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    background_tasks.add_task(sync_clicks_to_db, db)
    return {"message": "Sync started in background"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}