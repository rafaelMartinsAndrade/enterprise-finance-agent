FIRST_INVOICE = """Supplier: AWS Brasil Cloud
Hosting invoice for platform
Tax ID: 12.345.678/0001-01
Invoice: AWS-2026-090
Issue Date: 2026-07-16
Due Date: 2026-07-31
Amount: 899.90
"""

DUPLICATE_INVOICE = """Supplier: AWS Brasil Cloud
Hosting invoice duplicate candidate
Tax ID: 12.345.678/0001-01
Invoice: AWS-2026-090
Issue Date: 2026-07-17
Due Date: 2026-08-01
Amount: 899.90
"""


def test_agent_run_can_be_approved_after_human_review(client, acme_headers) -> None:
    created = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "AWS approval invoice", "tags": "cloud"},
        files={"file": ("aws-approval.txt", FIRST_INVOICE, "text/plain")},
    )
    run_id = created.json()["run_id"]

    detail = client.get(f"/api/v1/agent-runs/{run_id}", headers=acme_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "waiting_approval"
    assert body["approval_request"]["status"] == "pending"
    assert body["draft_pre_entry"]["status"] == "draft"
    assert body["supplier_match"]["supplier_code"] == "SUP-001"
    assert body["category_suggestion"]["category"] == "cloud"
    assert body["confidence_score"] >= 0.72
    assert [item["tool_name"] for item in body["tool_executions"]] == [
        "supplier_lookup",
        "duplicate_check",
        "categorize_document",
        "create_draft_pre_entry",
    ]
    assert len(body["llm_usage"]) == 2

    approved = client.post(
        f"/api/v1/agent-runs/{run_id}/resume",
        headers=acme_headers,
        json={"action": "approve", "notes": "Looks correct."},
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["status"] == "approved"
    assert approved_body["final_action"] == "approved"
    assert approved_body["approval_request"]["status"] == "approved"

    document = client.get(f"/api/v1/documents/{approved_body['document_id']}", headers=acme_headers)
    assert document.status_code == 200
    assert document.json()["status"] == "approved"


def test_agent_run_flags_duplicates_for_review(client, acme_headers) -> None:
    first = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "AWS baseline invoice", "tags": "cloud"},
        files={"file": ("aws-baseline.txt", FIRST_INVOICE, "text/plain")},
    )
    assert first.status_code == 202

    duplicate = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "AWS duplicate invoice", "tags": "cloud"},
        files={"file": ("aws-duplicate.txt", DUPLICATE_INVOICE, "text/plain")},
    )
    run_id = duplicate.json()["run_id"]

    detail = client.get(f"/api/v1/agent-runs/{run_id}", headers=acme_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "waiting_approval"
    assert len(body["duplicate_matches"]) == 1
    assert body["duplicate_matches"][0]["document_number"] == "AWS-2026-090"
    assert body["duplicate_matches"][0]["match_score"] >= 0.8
    assert body["approval_request"]["request_payload"]["recommended_action"] == "edit"
