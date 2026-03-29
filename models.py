# SQLAlchemy column types and ForeignKey for defining table schemas
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
# relationship links ORM models together (one-to-many between URL and Click)
from sqlalchemy.orm import relationship
from datetime import datetime
# Base class from database.py — all models must inherit from it to be tracked by SQLAlchemy
from database import Base

# Represents a shortened URL stored in the "urls" table
class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key = True, index = True)           # Auto-incrementing primary key
    short_code = Column(String, unique = True, index = True)         # The short code (must be unique)
    original_url = Column(String, nullable = False)                  # The destination URL
    created_at = Column(DateTime, default = datetime.utcnow)         # Timestamp set on creation
    expires_at = Column(DateTime, nullable = True, default = None)   # Optional expiry timestamp
    clicks = relationship("Click", back_populates="url")             # All clicks linked to this URL

# Represents a single click/visit recorded in the "clicks" table
class Click(Base):
    __tablename__ = "clicks"
    id = Column(Integer, primary_key = True, index = True)      # Auto-incrementing primary key
    click_date = Column(DateTime, default=datetime.utcnow)      # Timestamp of the click
    ip_address = Column(String, nullable = True)                # Visitor's IP address
    user_agent = Column(String, nullable = True)                # Visitor's browser/client info
    url_id = Column(Integer, ForeignKey("urls.id"))             # Foreign key linking to the URL record
    url = relationship("URL", back_populates="clicks")          # Back-reference to the parent URL