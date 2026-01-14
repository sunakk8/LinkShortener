from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from . import models, utils, database, schemas
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

@app.post("/shorten", response_model=schemas.URLResponse)
def create_short_url(url_request: schemas.URLCreate, db: Session = Depends(database.get_db)):
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
    # query db for url
    db_url = db.query(models.URL).filter(models.URL.short_code == short_code).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # update metrics
    db_url.clicks += 1
    db.commit()

    return RedirectResponse(url=db_url.target_url)
@app.get("/health")
def health_check():
    return {"status": "healthy"}