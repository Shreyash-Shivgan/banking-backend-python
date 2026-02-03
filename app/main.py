from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.accounts import accounts_db
import uuid

from app.users import users_db
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
from app.models import Account
from app.database import SessionLocal


app = FastAPI(title="Banking Backend API")
security = HTTPBearer()

# ---------------- Health ----------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------------- Auth ----------------
@app.post("/register")
def register(email: str, password: str):
    if email in users_db:
        raise HTTPException(status_code=400, detail="User already exists")

    users_db[email] = {
        "email": email,
        "password": hash_password(password),
        "role": "customer",
    }

    return {"message": "User registered successfully"}


@app.post("/login")
def login(email: str, password: str):
    user = users_db.get(email)

    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(data={"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)

    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=401)

    return user


@app.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "role": current_user["role"],
    }


# ---------------- Roles ----------------
def require_role(required_role: str):
    def checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] != required_role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return checker


@app.get("/admin/dashboard")
def admin_dashboard(current_user: dict = Depends(require_role("admin"))):
    return {"message": "Welcome Admin"}


@app.get("/customer/profile")
def customer_profile(current_user: dict = Depends(require_role("customer"))):
    return {"message": "Welcome Customer"}


# ---------------- Accounts ----------------
@app.post("/accounts/create")
def create_account(
    current_user: dict = Depends(require_role("customer"))
):
    account_number = str(uuid.uuid4())[:12]

    accounts_db[account_number] = {
        "account_number": account_number,
        "balance": 0.0,
        "owner_email": current_user["email"]
    }

    return accounts_db[account_number]

@app.post("/accounts/deposit")
def deposit(
    account_number: str,
    amount: float,
    current_user: dict = Depends(require_role("customer"))
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    account = accounts_db.get(account_number)

    if not account or account["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Account not found")

    account["balance"] += amount
    return account

@app.post("/accounts/withdraw")
def withdraw(
    account_number: str,
    amount: float,
    current_user: dict = Depends(require_role("customer"))
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    account = accounts_db.get(account_number)

    if not account or account["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Account not found")

    if account["balance"] < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    account["balance"] -= amount
    return account

@app.post("/accounts/transfer")
def transfer_money(
    from_account: str,
    to_account: str,
    amount: float,
    current_user: dict = Depends(require_role("customer"))
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    sender = accounts_db.get(from_account)
    receiver = accounts_db.get(to_account)

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Account not found")

    if sender["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Unauthorized account")

    if sender["balance"] < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # ---- ATOMIC SECTION ----
    try:
        sender["balance"] -= amount

        # simulate failure safety point
        receiver["balance"] += amount
    except Exception:
        # rollback
        sender["balance"] += amount
        raise HTTPException(status_code=500, detail="Transaction failed")

    return {
        "from": sender["account_number"],
        "to": receiver["account_number"],
        "amount": amount,
        "status": "success"
    }
