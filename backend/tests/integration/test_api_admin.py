from fastapi.testclient import TestClient

from app.main import app

app.state.limiter.enabled = False
client = TestClient(app)


def test_admin_routes_forbidden_for_non_admin():
    # Login as plain employee
    emp_login = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@company.com", "password": "Password@123"},
    )
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Plain employee should be blocked with 403 on all admin routes
    r_docs = client.get("/api/v1/admin/documents", headers=emp_headers)
    assert r_docs.status_code == 403

    r_users = client.get("/api/v1/admin/users", headers=emp_headers)
    assert r_users.status_code == 403

    r_audit = client.get("/api/v1/admin/audit", headers=emp_headers)
    assert r_audit.status_code == 403


def test_admin_routes_accessible_for_admin():
    # Login as admin
    adm_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "Admin@12345"},
    )
    adm_token = adm_login.json()["access_token"]
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # 1. Departments list
    r_depts = client.get("/api/v1/admin/departments", headers=adm_headers)
    assert r_depts.status_code == 200
    assert len(r_depts.json()) >= 5

    # 2. Documents list
    r_docs = client.get("/api/v1/admin/documents", headers=adm_headers)
    assert r_docs.status_code == 200
    assert isinstance(r_docs.json(), list)

    # 3. Users list
    r_users = client.get("/api/v1/admin/users", headers=adm_headers)
    assert r_users.status_code == 200
    assert any(u["email"] == "admin@company.com" for u in r_users.json())

    # 4. Audit logs list
    r_audit = client.get("/api/v1/admin/audit", headers=adm_headers)
    assert r_audit.status_code == 200
    data = r_audit.json()
    assert "items" in data
    assert "total" in data
