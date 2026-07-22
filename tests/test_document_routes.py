AWS_INVOICE = """Supplier: AWS Brasil Cloud
Hosting invoice for July
Tax ID: 12.345.678/0001-01
Invoice: AWS-2026-071
Issue Date: 2026-07-15
Due Date: 2026-07-30
Amount: 1499.90
"""

RETRY_INVOICE = """Supplier: retry-me telecom
Internet service unstable
Invoice: FAIL-2026-01
Issue Date: 2026-07-10
Due Date: 2026-07-25
Amount: 199.90
"""


def test_upload_document_creates_waiting_approval_run_and_honors_idempotency(client, acme_headers) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "AWS July invoice", "tags": "cloud,july", "idempotency_key": "upload-001"},
        files={"file": ("aws-invoice.txt", AWS_INVOICE, "text/plain")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "waiting_approval"

    listing = client.get("/api/v1/documents", headers=acme_headers)
    assert listing.status_code == 200
    assert listing.json()[0]["latest_run_id"] == payload["run_id"]

    detail = client.get(f"/api/v1/documents/{payload['document_id']}", headers=acme_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "waiting_approval"
    assert body["tags"] == ["cloud", "july"]
    assert body["versions"][0]["page_count"] == 1
    assert body["versions"][0]["character_count"] > 30

    repeated = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "AWS July invoice", "tags": "cloud,july", "idempotency_key": "upload-001"},
        files={"file": ("aws-invoice.txt", AWS_INVOICE, "text/plain")},
    )
    assert repeated.status_code == 202
    assert repeated.json() == payload


def test_update_document_rejects_identical_content(client, acme_headers) -> None:
    created = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "AWS July invoice", "tags": "cloud"},
        files={"file": ("aws-invoice.txt", AWS_INVOICE, "text/plain")},
    )
    document_id = created.json()["document_id"]

    response = client.put(
        f"/api/v1/documents/{document_id}",
        headers=acme_headers,
        data={"title": "AWS July invoice"},
        files={"file": ("aws-invoice.txt", AWS_INVOICE, "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "domain_validation_error"


def test_upload_document_returns_failed_run_when_tool_retries_exhaust(client, acme_headers) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "Retry failure invoice", "tags": "telecom"},
        files={"file": ("retry-invoice.txt", RETRY_INVOICE, "text/plain")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "failed"

    run = client.get(f"/api/v1/agent-runs/{payload['run_id']}", headers=acme_headers)
    assert run.status_code == 200
    run_body = run.json()
    assert run_body["status"] == "failed"
    assert run_body["last_error_message"] == "Transient supplier registry failure."
    assert run_body["tool_executions"][0]["tool_name"] == "supplier_lookup"
    assert run_body["tool_executions"][0]["status"] == "failed"
    assert run_body["tool_executions"][0]["arguments"]["attempts"] == 3
