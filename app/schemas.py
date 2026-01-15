from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

class URLCreate(BaseModel):
    target_url: HttpUrl
    custom_url: Optional[str] = Field(
        None,
        min_length=3,
        max_length=20,
        pattern="^[a-zA-Z0-9_-]+$"
    )

class URLResponse(BaseModel):
    short_url: str
    target_url: str

    class Config:
        from_attributes = True