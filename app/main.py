from fastapi import FastAPI, HTTPException
from app.users import users_db
from app.security import hash_password, verify_password
from app.security import create_access_token
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.security import SECRET_KEY, ALGORITHM

app = FastAPI(title="Banking Backend API")
security = HTTPBearer()

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

    access_token = create_access_token(
    data={"sub": user["email"]}
    )
    return {
    "access_token": access_token,
    "token_type": "bearer"
    }

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = users_db.get(email)
    if user is None:
        raise credentials_exception

    return user

@app.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "role": current_user["role"]
    }
