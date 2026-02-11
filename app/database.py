import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.base import Base  # ✅ Base comes from here

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # ✅ THIS WAS MISSING

engine = create_engine(
    DATABASE_URL,
    echo=True,   # You can change to False in production
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")
