# FastAPI framework and utilities for building the API
from fastapi import FastAPI, HTTPException, Depends, Request
# Pydantic for request body validation; HttpUrl validates URLs, field_validator for custom rules
from pydantic import BaseModel, HttpUrl, field_validator
import string
import random
# RedirectResponse sends the user to the original URL
from fastapi.responses import RedirectResponse
# Database setup: engine (connects to DB), SessionLocal (creates sessions), Base (ORM base class)
from database import engine, SessionLocal, Base
# ORM models for the URL and Click tables
from models import URL, Click
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta, timezone

# Create all database tables defined in models if they don't already exist
Base.metadata.create_all(bind = engine)

# Request body schema for POST /url
class URLRequest(BaseModel):
    url: HttpUrl                          # Must be a valid URL
    custom_code: Optional[str] = None    # Optional user-defined short code
    expires_in_minutes: Optional[int] = None  # Optional expiry duration in minutes

    @field_validator("custom_code")
    @classmethod
    def check_custom_code(cls, cc):
        if cc == None:
            return None
        # Only allow letters and numbers in custom codes
        if not cc.isalnum():
            raise ValueError("Custom code must be alpha numeric")
        # Enforce length between 4 and 14 characters (exclusive bounds)
        if not 3 < len(cc) < 15:
            raise ValueError("Custom code must be between 3 and 15 in length")
        return cc


# Dependency that provides a database session and ensures it is closed after each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Generates a random 6-character alphanumeric short code
def generate_short_code():
    chars = string.ascii_letters + string.digits
    rand_chars = random.choices(chars, k = 6)
    rand_url = "".join(rand_chars)
    return rand_url

app = FastAPI()

# Returns every URL record in the database
@app.get("/all")
def get_all(db: Session = Depends(get_db)):
    return db.query(URL).all()

# Returns click analytics for a given short code
@app.get("/stats/{code}")
def get_stats(code: str, db: Session = Depends(get_db)):
    code_entry = db.query(URL).filter(code == URL.short_code).first()
    if code_entry:
        # Build a list of click details from the related Click records
        click_list = []
        for click in code_entry.clicks:
            click_list.append({"time": click.click_date,"ip": click.ip_address, "agent": click.user_agent})
        return {"short_code": code, "original_url": code_entry.original_url, "total_clicks": len(click_list), "clicks": click_list, "expires_at": code_entry.expires_at}
    else:
        raise HTTPException(status_code=404, detail="Short code does not exist")


# Creates a new shortened URL, optionally with a custom code and expiry
@app.post("/url")
def url_request(request: URLRequest, db: Session = Depends(get_db)):
    # Calculate expiry timestamp if a duration was provided
    if request.expires_in_minutes is not None:
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes = request.expires_in_minutes)
    else:
        expires_at = None

    if request.custom_code:
        # Check that the custom code isn't already taken
        code_entry = db.query(URL).filter(request.custom_code == URL.short_code).first()
        if code_entry:
            raise HTTPException(status_code = 409, detail = "Custom code already exists")
        new_url = URL(short_code = request.custom_code, original_url = str(request.url), expires_at = expires_at)
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
        return {"short_code": request.custom_code,
                "short_url": "http://127.0.0.1:8000/short_url/" + request.custom_code,
                "original_url": str(request.url),
                "expires_at": expires_at}
    else:
        # Generate a random code, retrying on the rare chance of a collision
        code = generate_short_code()
        while db.query(URL).filter(URL.short_code == code).first() is not None:
            code = generate_short_code()
        new_url = URL(short_code = code, original_url = str(request.url), expires_at = expires_at)
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
        return {"short_code": code,
                "short_url": "http://127.0.0.1:8000/short_url/" + code,
                "original_url": str(request.url),
                "expires_at": expires_at}

# Redirects the user to the original URL and records the click
@app.get("/short_url/{code}")
def shortener(code: str, request: Request, db: Session = Depends(get_db)):
    url_entry = db.query(URL).filter(URL.short_code == code).first()
    if url_entry:
        # Reject the request if the link has passed its expiry time
        if url_entry.expires_at is not None and datetime.now(timezone.utc).replace(tzinfo=None) > url_entry.expires_at:
            raise HTTPException(status_code=410, detail="This link has expired")
        # Log the click with the visitor's IP and browser user-agent
        new_click = Click(url_id = url_entry.id, ip_address = request.client.host, user_agent = request.headers.get("user-agent"))
        db.add(new_click)
        db.commit()
        return RedirectResponse(url_entry.original_url)
    raise HTTPException(status_code = 404, detail = "Could not access website")



