from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True

class AccountResponse(BaseModel):
    id: int
    account_number: str
    balance: float

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    from_account: Optional[str]
    to_account: Optional[str]
    amount: float
    type: str
    timestamp: datetime

    class Config:
        from_attributes = True