from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.base import Base
from datetime import datetime


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_account = Column(String, nullable=True)
    to_account = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # deposit / withdraw / transfer
    timestamp = Column(DateTime, default=datetime.utcnow)
