from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import uuid
from app.database import engine
from app.base import Base
from app.users import User
from app.accounts import Account
from app.transactions import Transaction
Base.metadata.create_all(bind=engine)
from app.database import Base, engine, SessionLocal
from app.schemas import AccountResponse
from typing import List
from fastapi import Query
from app.schemas import TransactionResponse
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)

# ---------- DB setup ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- App ----------
app = FastAPI(title="Banking Backend API")
security = HTTPBearer()

# ---------- Health ----------
@app.get("/health")
def health_check():
    return {"status": "ok"}

# ---------- Auth ----------
@app.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role="customer",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered successfully"}

@app.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401)

    return user

@app.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }

# ---------- Roles ----------
def require_role(required_role: str):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return checker

# ---------- Accounts ----------
@app.post("/accounts/create", response_model=AccountResponse)
def create_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_account = Account(
        account_number=str(uuid.uuid4())[:12],
        balance=0.0,
        user_id=current_user.id,
    )

    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return new_account   # ✅ This fixes it

@app.post("/accounts/deposit", response_model=AccountResponse)
def deposit(
    account_number: str,
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    account = (
        db.query(Account)
        .filter(Account.account_number == account_number)
        .first()
    )

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.balance += amount

    # 🔥 LOG TRANSACTION
    transaction = Transaction(
        from_account=None,
        to_account=account.account_number,
        amount=amount,
        type="deposit"
    )

    db.add(transaction)
    db.commit()
    db.refresh(account)

    return account

@app.post("/accounts/withdraw")
def withdraw(
    account_number: str,
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    account = (
        db.query(Account)
        .filter(Account.account_number == account_number)
        .first()
    )

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    account.balance -= amount

    # 🔥 LOG TRANSACTION
    transaction = Transaction(
        from_account=account.account_number,
        to_account=None,
        amount=amount,
        type="withdraw"
    )

    db.add(transaction)
    db.commit()
    db.refresh(account)

    return account

@app.post("/accounts/transfer")
def transfer(
    from_account: str,
    to_account: str,
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    try:
        sender = (
            db.query(Account)
            .filter(Account.account_number == from_account)
            .with_for_update()
            .first()
        )

        receiver = (
            db.query(Account)
            .filter(Account.account_number == to_account)
            .with_for_update()
            .first()
        )

        if not sender or not receiver:
            raise HTTPException(status_code=404, detail="Account not found")

        if sender.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # 🔥 UPDATE BALANCES
        sender.balance -= amount
        receiver.balance += amount

        # 🔥 LOG TRANSACTION (SINGLE RECORD)
        transaction = Transaction(
            from_account=sender.account_number,
            to_account=receiver.account_number,
            amount=amount,
            type="transfer"
        )

        db.add(transaction)
        db.commit()

        return {
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount
        }

    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transfer failed")

@app.get("/transactions", response_model=list[TransactionResponse])
def transaction_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    query = db.query(Transaction)

    # If user is NOT admin → filter their transactions only
    if current_user.role != "admin":

        # Get all accounts of this user
        user_accounts = (
            db.query(Account)
            .filter(Account.user_id == current_user.id)
            .all()
        )

        account_numbers = [acc.account_number for acc in user_accounts]

        query = query.filter(
            (Transaction.from_account.in_(account_numbers)) |
            (Transaction.to_account.in_(account_numbers))
        )

    transactions = (
        query
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return transactions

@app.get("/accounts/balance")
def check_balance(
    account_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = (
        db.query(Account)
        .filter(
            Account.account_number == account_number,
            Account.user_id == current_user.id,
        )
        .first()
    )

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "account_number": account.account_number,
        "balance": account.balance,
    }