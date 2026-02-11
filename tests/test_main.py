from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login():
    response = client.post(
        "/login",
        params={"email": "a@gmail.com", "password": "1234"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_deposit():
    # Login
    login = client.post(
        "/login",
        params={"email": "a@gmail.com", "password": "1234"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create account first
    create = client.post("/accounts/create", headers=headers)
    account_number = create.json()["account_number"]

    # Now deposit
    response = client.post(
        "/accounts/deposit",
        params={"account_number": account_number, "amount": 100},
        headers=headers,
    )

    assert response.status_code == 200

def test_transfer():
    login = client.post(
        "/login",
        params={"email": "a@gmail.com", "password": "1234"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create two accounts
    acc1 = client.post("/accounts/create", headers=headers).json()["account_number"]
    acc2 = client.post("/accounts/create", headers=headers).json()["account_number"]

    # Deposit into first account
    client.post(
        "/accounts/deposit",
        params={"account_number": acc1, "amount": 200},
        headers=headers,
    )

    # Transfer
    response = client.post(
        "/accounts/transfer",
        params={
            "from_account": acc1,
            "to_account": acc2,
            "amount": 50
        },
        headers=headers,
    )

    assert response.status_code == 200
