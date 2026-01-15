from pydantic import BaseModel, HttpUrl
from typing import Optional

class URLCreate(BaseModel):
    target_url: HttpUrl
    custom_alias: Optional[str] = None

class URLResponse(BaseModel):
    short_url: str
    target_url: str

    class Config:
        from_attributes = True