from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key = True, index = True)
    short_code = Column(String, unique = True, index = True)
    original_url = Column(String, nullable = False)
    created_at = Column(DateTime, default = datetime.utcnow)
    clicks = relationship("Click", back_populates="url")

class Click(Base):
    __tablename__ = "clicks"
    id = Column(Integer, primary_key=True, index=True)
    click_date = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    url_id = Column(Integer, ForeignKey("urls.id"))
    url = relationship("URL", back_populates="clicks")