from fastapi.testclient import TestClient

from app.main import app

app.state.limiter.enabled = False
client = TestClient(app)


def test_auth_login_success_and_cookie():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "Password@123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "employee@company.com"
    assert data["user"]["is_admin"] is False
    assert "refresh_token" in response.cookies


def test_auth_login_invalid_password():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_auth_refresh_and_logout():
    # 1. Login to get cookies
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "Admin@12345"},
    )
    assert login_resp.status_code == 200
    cookies = login_resp.cookies

    # 2. Refresh token
    refresh_resp = client.post("/api/v1/auth/refresh", cookies=cookies)
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data
    new_cookies = refresh_resp.cookies

    # 3. Logout
    logout_resp = client.post("/api/v1/auth/logout", cookies=new_cookies)
    assert logout_resp.status_code == 200

    # 4. Old refresh token should now be rejected
    fail_refresh = client.post("/api/v1/auth/refresh", cookies=new_cookies)
    assert fail_refresh.status_code == 401


def test_get_me_endpoint():
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "Admin@12345"},
    )
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "admin@company.com"
    assert me_data["is_admin"] is True


def test_conversation_lifecycle_and_user_isolation():
    # Login as User A (employee)
    emp_login = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "Password@123"},
    )
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Login as User B (admin)
    adm_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "Admin@12345"},
    )
    adm_token = adm_login.json()["access_token"]
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # 1. User A creates conversation
    create_resp = client.post(
        "/api/v1/conversations",
        json={"title": "Employee Private Thread"},
        headers=emp_headers,
    )
    assert create_resp.status_code == 200
    conv_id = create_resp.json()["id"]

    # 2. User A can list and get it
    list_resp = client.get("/api/v1/conversations", headers=emp_headers)
    assert list_resp.status_code == 200
    assert any(c["id"] == conv_id for c in list_resp.json())

    # 3. User B cannot see or get User A's conversation (isolation)
    b_get = client.get(f"/api/v1/conversations/{conv_id}", headers=adm_headers)
    assert b_get.status_code == 404

    # 4. User A renames conversation
    patch_resp = client.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "Renamed Thread"},
        headers=emp_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Renamed Thread"

    # 5. User A deletes conversation
    del_resp = client.delete(f"/api/v1/conversations/{conv_id}", headers=emp_headers)
    assert del_resp.status_code == 200
