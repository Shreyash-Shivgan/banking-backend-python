from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# -------------------
# USER
# -------------------

class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True


# -------------------
# ACCOUNT
# -------------------

class AccountResponse(BaseModel):
    id: int
    account_number: str
    balance: float

    class Config:
        from_attributes = True


# -------------------
# TRANSACTION
# -------------------

class TransactionResponse(BaseModel):
    id: int
    from_account: Optional[str]
    to_account: Optional[str]
    amount: float
    type: str
    timestamp: datetime

    class Config:
        from_attributes = True
