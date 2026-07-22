import os
from pathlib import Path

import httpx
import streamlit as st


API_BASE_URL = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
DEFAULT_TOKEN = os.getenv("API_TOKEN", "change-me")
DEMO_USERS = {
    "acme-finance": "ana@acme.demo",
    "northwind-ops": "bruno@northwind.demo",
}
DEMO_FILES = {
    "High confidence invoice": Path("demo_data/documents/acme-finance/aws_invoice.txt"),
    "Ambiguous supplier": Path("demo_data/documents/acme-finance/ambiguous_supplier_invoice.txt"),
    "Duplicate risk": Path("demo_data/documents/acme-finance/duplicate_invoice.txt"),
    "Retry scenario": Path("demo_data/documents/acme-finance/retry_supplier_invoice.txt"),
}


st.set_page_config(page_title="Enterprise Finance Agent", page_icon="🧾", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(14, 165, 233, 0.16), transparent 32%),
            radial-gradient(circle at top right, rgba(249, 115, 22, 0.18), transparent 34%),
            linear-gradient(180deg, #f8fafc 0%, #fffaf0 100%);
        color: #172554;
        font-family: "Aptos", "Trebuchet MS", sans-serif;
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(15,23,42,0.94), rgba(30,41,59,0.86));
        color: #f8fafc;
        box-shadow: 0 22px 60px rgba(15, 23, 42, 0.18);
        margin-bottom: 1rem;
    }
    .card {
        background: rgba(255,255,255,0.84);
        border: 1px solid rgba(148,163,184,0.22);
        border-radius: 20px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 35px rgba(15, 23, 42, 0.08);
    }
    </style>
    <div class="hero">
        <h1>Enterprise Finance Agent</h1>
        <p>Validated tools, LangGraph checkpoints, human approval, and draft-only automation.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def build_headers(organization_slug: str, user_email: str, token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Slug": organization_slug,
        "X-User-Email": user_email,
    }


def api_get(path: str, *, headers: dict[str, str]) -> httpx.Response:
    with httpx.Client(timeout=30.0) as client:
        return client.get(f"{API_BASE_URL}{path}", headers=headers)


def api_post(path: str, *, headers: dict[str, str], **kwargs) -> httpx.Response:
    with httpx.Client(timeout=60.0) as client:
        return client.post(f"{API_BASE_URL}{path}", headers=headers, **kwargs)


def upload_demo(document_label: str, organization_slug: str, user_email: str, token: str) -> tuple[bool, str]:
    file_path = DEMO_FILES[document_label]
    headers = build_headers(organization_slug, user_email, token)
    with file_path.open("rb") as handle:
        response = api_post(
            "/documents/upload",
            headers=headers,
            data={
                "title": file_path.stem.replace("_", " ").title(),
                "tags": "demo,finance-agent",
                "idempotency_key": file_path.stem,
            },
            files={"file": (file_path.name, handle, "text/plain")},
        )
    if response.is_success:
        payload = response.json()
        return True, f"run {payload['run_id']} started for document {payload['document_id']}"
    return False, response.text


def list_runs(organization_slug: str, user_email: str, token: str) -> list[dict]:
    headers = build_headers(organization_slug, user_email, token)
    response = api_get("/agent-runs", headers=headers)
    response.raise_for_status()
    return response.json()


def get_run(run_id: int, organization_slug: str, user_email: str, token: str) -> dict:
    headers = build_headers(organization_slug, user_email, token)
    response = api_get(f"/agent-runs/{run_id}", headers=headers)
    response.raise_for_status()
    return response.json()


def resume_run(run_id: int, action: str, organization_slug: str, user_email: str, token: str, edited_fields: dict | None = None, notes: str | None = None) -> dict:
    headers = build_headers(organization_slug, user_email, token)
    response = api_post(
        f"/agent-runs/{run_id}/resume",
        headers=headers,
        json={"action": action, "notes": notes, "edited_fields": edited_fields},
    )
    response.raise_for_status()
    return response.json()


with st.sidebar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    organization_slug = st.selectbox("Tenant", ["acme-finance", "northwind-ops"])
    user_email = st.text_input("User email", value=DEMO_USERS[organization_slug])
    api_token = st.text_input("API token", value=DEFAULT_TOKEN, type="password")
    st.caption(f"API base: {API_BASE_URL}")
    st.markdown("</div>", unsafe_allow_html=True)


left, right = st.columns([0.95, 1.35], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Demo scenarios")
    scenario = st.selectbox("Upload scenario", list(DEMO_FILES))
    if st.button("Start workflow", use_container_width=True):
        ok, detail = upload_demo(scenario, organization_slug, user_email, api_token)
        if ok:
            st.success(detail)
        else:
            st.error(detail)

    if st.button("Refresh runs", use_container_width=True):
        st.session_state["runs"] = list_runs(organization_slug, user_email, api_token)

    st.divider()
    st.subheader("Recent runs")
    runs = st.session_state.get("runs", [])
    for item in runs:
        if st.button(f"Open run {item['id']} | {item['status']}", key=f"run-{item['id']}"):
            st.session_state["selected_run"] = get_run(item["id"], organization_slug, user_email, api_token)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Approval review")
    run = st.session_state.get("selected_run")
    if run:
        st.markdown(f"**Run {run['id']}** | status `{run['status']}` | confidence `{run['confidence_score']}`")
        st.json(run["extracted_fields"])
        if run["supplier_match"]:
            st.markdown("### Supplier match")
            st.json(run["supplier_match"])
        if run["duplicate_matches"]:
            st.markdown("### Duplicate matches")
            st.json(run["duplicate_matches"])
        if run["category_suggestion"]:
            st.markdown("### Category suggestion")
            st.json(run["category_suggestion"])
        if run["confidence_breakdown"]:
            st.markdown("### Confidence")
            st.json(run["confidence_breakdown"])
        st.markdown("### Tool audit")
        st.json(run["tool_executions"])

        if run["status"] == "waiting_approval":
            notes = st.text_area("Reviewer notes", value="")
            edit_due_date = st.text_input("Edited due date", value=run["extracted_fields"].get("due_date") or "")
            edit_category = st.text_input("Edited category", value=(run["category_suggestion"] or {}).get("category", ""))
            col1, col2, col3 = st.columns(3)
            if col1.button("Approve", use_container_width=True):
                st.session_state["selected_run"] = resume_run(run["id"], "approve", organization_slug, user_email, api_token, notes=notes)
            if col2.button("Reject", use_container_width=True):
                st.session_state["selected_run"] = resume_run(run["id"], "reject", organization_slug, user_email, api_token, notes=notes)
            if col3.button("Edit and Approve", use_container_width=True):
                edited_fields = {"due_date": edit_due_date or None, "description": run["extracted_fields"].get("description"), "category": edit_category or None}
                st.session_state["selected_run"] = resume_run(run["id"], "edit", organization_slug, user_email, api_token, edited_fields=edited_fields, notes=notes)
    else:
        st.info("Pick a run from the left panel.")
    st.markdown("</div>", unsafe_allow_html=True)
