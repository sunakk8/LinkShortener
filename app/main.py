# app/main.py
from fastapi import FastAPI
import os

app = FastAPI(title="URL Shortener")

@app.get("/")
def read_root():
    return {
        "message": "URL Shortener API is live",
        "salt_check": "Salt is set" if os.getenv("salt") else "Salt is missing"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}