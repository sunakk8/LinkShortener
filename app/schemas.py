from pydantic import BaseModel, HttpUrl

class URLCreate(BaseModel):
    target_url: HttpUrl

class URLResponse(BaseModel):
    short_url: str
    target_url: str

    class Config:
        from_attributes = True