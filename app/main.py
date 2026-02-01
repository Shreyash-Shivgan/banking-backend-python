from fastapi import FastAPI, HTTPException
from app.users import users_db
from app.security import hash_password, verify_password

app = FastAPI(title="Banking Backend API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/register")
def register(email: str, password: str):
    if email in users_db:
        raise HTTPException(status_code=400, detail="User already exists")

    users_db[email] = {
        "email": email,
        "password": hash_password(password),
        "role": "customer"
    }

    return {"message": "User registered successfully"}

@app.post("/login")
def login(email: str, password: str):
    user = users_db.get(email)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return {"message": "Login successful"}
