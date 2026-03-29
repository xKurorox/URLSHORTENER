# SQLAlchemy core: create_engine connects to the database
from sqlalchemy import create_engine
# sessionmaker creates DB session factories; declarative_base is the base class for ORM models
from sqlalchemy.orm import sessionmaker, declarative_base

# Connect to a local SQLite file (url.db); check_same_thread=False allows use across FastAPI threads
engine = create_engine("sqlite:///./url.db", connect_args = {"check_same_thread": False})

# Session factory — autocommit off so transactions are explicit (committed or rolled back manually)
SessionLocal = sessionmaker(autocommit = False, bind = engine)

# Base class that all ORM models inherit from so SQLAlchemy can track them
Base = declarative_base()
