# T57 Enterprise Finance Agent

Enterprise finance workflow agent for invoice intake. FastAPI backend, LangGraph state orchestration, validated tools, draft-only automation, human approval, durable checkpoints, Streamlit review UI.

## Scope

Steps covered in this repo:

- `T57` to `T58`: business process and autonomy boundaries
- `T59` to `T60`: agent state model plus LangGraph workflow
- `T61` to `T64`: supplier lookup, duplicate detection, categorization, draft pre-entry tools
- `T65` to `T75`: structured outputs, argument validation, confidence, conditionals, approval, persistence, resume, retries, idempotency, audit, step limit
- `T76` to `T81`: tests, approval UI, demo scenarios, diagram, video script, publish pack

## Business Problem

Accounts payable teams receive invoices and receipts that still demand repetitive manual triage: identify supplier, detect duplicates, choose category, and create a safe draft entry before approval. This project automates the analysis while keeping humans in control of any final decision.

## Autonomy Limits

- Agent may extract fields, query supplier registry, check duplicates, suggest category, and create only a draft pre-entry.
- Agent may recommend approve, reject, or edit.
- Agent never posts a final accounting entry without human approval.
- Agent never crosses tenant boundaries.

## Stack

- Python 3.11+
- FastAPI
- LangGraph
- SQLite checkpoint saver for durable pause/resume
- PostgreSQL for app data
- OpenAI SDK or mock providers
- Streamlit
- Pytest

## Workflow

1. Upload finance document.
2. Extract structured invoice fields.
3. Lookup supplier with validated tool args.
4. Check duplicate risk against existing drafts.
5. Suggest category with rules or LLM.
6. Compute confidence from real signals.
7. Create draft pre-entry only.
8. Pause with `interrupt()` for human review.
9. Resume with approve, reject, or edit.
10. Persist audit trail, state, and final status.

See [docs/architecture.md](docs/architecture.md).

## API Surface

Base prefix: `/api/v1`

Public:

- `GET /health`
- `POST /auth/demo-login`

Tenant protected with `Authorization`, `X-Organization-Slug`, `X-User-Email`:

- `GET /organizations`
- `GET /organizations/{organization_slug}/users`
- `GET /suppliers`
- `GET /documents`
- `GET /documents/{document_id}`
- `POST /documents/upload`
- `PUT /documents/{document_id}`
- `GET /agent-runs`
- `GET /agent-runs/{run_id}`
- `POST /agent-runs/{run_id}/resume`

## Local Run

```bash
python -m pip install -e ".[dev]"
alembic upgrade head
seed-demo
uvicorn app.main:app --reload --app-dir src
streamlit run streamlit_app.py
```

## Docker Run

```bash
docker compose up --build
docker compose exec api seed-demo
```

URLs:

- API docs: `http://localhost:8000/docs`
- UI: `http://localhost:8501`

## Demo Assets

- Scenario docs: `demo_data/documents/acme-finance/`
- Curl examples: `examples/upload_finance_document_curl.sh`, `examples/approve_run_curl.sh`
- Video script: [docs/demo-video-script.md](docs/demo-video-script.md)
- Publish list: [docs/publish-checklist.md](docs/publish-checklist.md)

## Human Review Paths

- Approve: keep extracted draft as-is.
- Reject: mark run and draft as rejected.
- Edit: reviewer adjusts fields and resumes from checkpoint without replaying previous side effects.

## Testing

```bash
pytest
```

Covered flows:

- normal approval path
- duplicate detection path
- retryable supplier lookup
- idempotent upload start
- tenant isolation
- update validation protections

## Publish

Repo URL:

- [rafaelMartinsAndrade/enterprise-finance-agent](https://github.com/rafaelMartinsAndrade/enterprise-finance-agent)
