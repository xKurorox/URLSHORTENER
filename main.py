from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator
import string
import random
from fastapi.responses import RedirectResponse
from database import engine, SessionLocal, Base
from models import URL, Click
from sqlalchemy.orm import Session
from typing import Optional

Base.metadata.create_all(bind = engine)

class URLRequest(BaseModel):
    url: str
    custom_code: Optional[str] = None
    @field_validator("custom_code")
    @classmethod
    def check_custom_code(cls, cc):
        if cc == None:
            return None
        if not cc.isalnum():
            raise ValueError("Custom code must be alpha numeric")
        if not 3 < len(cc) < 15:
            raise ValueError("Custom code must be between 3 and 15 in length")
        return cc


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_short_code():    
    chars = string.ascii_letters + string.digits
    rand_chars = random.choices(chars, k = 6)
    rand_url = "".join(rand_chars)
    return rand_url

app = FastAPI()

@app.get("/all")
def get_all(db: Session = Depends(get_db)):
    return db.query(URL).all()

@app.get("/stats/{code}")
def get_stats(code: str, db: Session = Depends(get_db)):
    code_entry = db.query(URL).filter(code == URL.short_code).first()
    if code_entry:
        click_list = []
        for click in code_entry.clicks:
            click_list.append({"time": click.click_date,"ip": click.ip_address, "agent": click.user_agent})
        return {"short_code": code, "original_url": code_entry.original_url, "total_clicks": len(click_list), "clicks": click_list}
    else:
        raise HTTPException(status_code=404, detail="Short code does not exist")


@app.post("/url")
def url_request(request: URLRequest, db: Session = Depends(get_db)):
    if request.custom_code:
        code_entry = db.query(URL).filter(request.custom_code == URL.short_code).first()
        if code_entry:
            raise HTTPException(status_code = 409, detail = "Custom code already exists")
        new_url = URL(short_code = request.custom_code, original_url = request.url)
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
        return {"short_code": request.custom_code,
                "short_url": "http://127.0.0.1:8000/short_url/" + request.custom_code,
                "original_url": request.url}
    else:
        code = generate_short_code()
        while db.query(URL).filter(URL.short_code == code).first() is not None:
            code = generate_short_code()
        new_url = URL(short_code = code, original_url = request.url)
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
        return {"short_code": code,
                "short_url": "http://127.0.0.1:8000/short_url/" + code,
                "original_url": request.url}

@app.get("/short_url/{code}")
def shortener(code: str, request: Request, db: Session = Depends(get_db)):
    url_entry = db.query(URL).filter(URL.short_code == code).first()
    if url_entry:
        new_click = Click(url_id = url_entry.id, ip_address = request.client.host, user_agent = request.headers.get("user-agent"))
        db.add(new_click)
        db.commit()
        return RedirectResponse(url_entry.original_url)
    raise HTTPException(status_code = 404, detail = "Could not access website")



