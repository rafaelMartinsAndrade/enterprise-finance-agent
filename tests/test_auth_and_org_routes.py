def test_demo_login_and_org_listing(client) -> None:
    orgs = client.get(
        "/api/v1/organizations",
        headers={"Authorization": "Bearer change-me"},
    )
    assert orgs.status_code == 200
    assert {item["slug"] for item in orgs.json()} == {"acme-finance", "northwind-ops"}

    users = client.get(
        "/api/v1/organizations/acme-finance/users",
        headers={"Authorization": "Bearer change-me"},
    )
    assert users.status_code == 200
    assert users.json()[0]["email"] == "ana@acme.test"

    login = client.post(
        "/api/v1/auth/demo-login",
        json={"organization_slug": "acme-finance", "user_email": "ana@acme.test"},
    )
    assert login.status_code == 200
    assert login.json()["tenant"]["organization_slug"] == "acme-finance"
