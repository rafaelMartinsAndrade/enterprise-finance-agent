def test_suppliers_route_is_tenant_scoped(client, acme_headers, northwind_headers) -> None:
    acme = client.get("/api/v1/suppliers", headers=acme_headers)
    northwind = client.get("/api/v1/suppliers", headers=northwind_headers)

    assert acme.status_code == 200
    assert northwind.status_code == 200
    assert [item["supplier_code"] for item in acme.json()] == ["SUP-001", "SUP-003", "SUP-002"]
    assert [item["supplier_code"] for item in northwind.json()] == ["SUP-900"]
