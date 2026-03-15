from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import string
import random
from fastapi.responses import RedirectResponse
from database import engine, SessionLocal, Base
from models import URL
from sqlalchemy.orm import Session

Base.metadata.create_all(bind = engine)

class URLRequest(BaseModel):
    url: str

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

@app.post("/url")
def url_request(request: URLRequest, db: Session = Depends(get_db)):
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
def shortener(code: str, db: Session = Depends(get_db)):
    url_entry = db.query(URL).filter(URL.short_code == code).first()
    if url_entry:
        return RedirectResponse(url_entry.original_url)
    raise HTTPException(status_code = 404, detail = "Could not access website")



