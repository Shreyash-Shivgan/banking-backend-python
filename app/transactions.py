from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_account = Column(String)
    to_account = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
