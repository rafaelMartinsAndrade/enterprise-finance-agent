from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.middleware import register_middleware
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="1.0.0",
    summary="Enterprise finance workflow agent for invoice triage, duplicate checks, and draft pre-entry approval.",
    description=(
        "Enterprise finance workflow backend with LangGraph state orchestration, durable checkpoints, "
        "supplier lookup, duplicate detection, category suggestion, draft pre-entry creation, and human approval."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Demo login and tenant context helpers."},
        {"name": "health", "description": "Operational health endpoints."},
        {"name": "organizations", "description": "Organization and user discovery endpoints."},
        {"name": "suppliers", "description": "Supplier registry endpoints for the finance agent."},
        {"name": "documents", "description": "Finance document upload and version history endpoints."},
        {"name": "agent-runs", "description": "Agent workflow execution, approval, and audit endpoints."},
    ],
)
register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)
