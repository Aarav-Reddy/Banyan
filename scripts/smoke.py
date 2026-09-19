import os

import httpx

url = os.getenv("PHILANTHRA_BASE_URL", "http://127.0.0.1:8080")
with httpx.Client(base_url=url, timeout=20) as client:
    assert client.get("/api/health/").status_code == 200
    assert client.get("/api/ready/").status_code == 200
    session = client.get("/api/v1/session/").json()["data"]
    token = session["csrfToken"]
    result = client.post(
        "/api/v1/login/",
        json={"username": "foundation-admin", "password": "Demo-only-Philanthra-2026!"},
        headers={"X-CSRFToken": token, "Origin": url},
    )
    assert result.status_code == 200, result.text
    session = client.get("/api/v1/session/").json()["data"]
    headers = {"X-Workspace-ID": session["workspaces"][0]["id"]}
    response = client.get("/api/v1/organizations/", headers=headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) >= 20
    print("PASS readiness, session/CSRF login and persisted organization discovery")
