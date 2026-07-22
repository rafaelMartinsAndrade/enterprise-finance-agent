def test_health_route(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}
    assert response.json()["app"] == "enterprise-finance-agent"
    assert response.json()["checkpointing"] == "ready"
