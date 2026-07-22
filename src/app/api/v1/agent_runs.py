from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_tenant_context
from app.core.db import get_db
from app.schemas.agent import AgentRunListItem, AgentRunResponse, ApprovalDecisionRequest
from app.schemas.auth import TenantContext
from app.services.workflow_service import WorkflowService


router = APIRouter()


@router.get("", response_model=list[AgentRunListItem], summary="List tenant agent workflow runs")
def list_runs(
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> list[AgentRunListItem]:
    return WorkflowService(db).list_runs(tenant=tenant)


@router.get("/{run_id}", response_model=AgentRunResponse, summary="Get workflow run with tool audit and approval state")
def get_run(
    run_id: int,
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    return WorkflowService(db).get_run(tenant=tenant, run_id=run_id)


@router.post("/{run_id}/resume", response_model=AgentRunResponse, summary="Approve, reject, or edit paused workflow")
def resume_run(
    run_id: int,
    payload: ApprovalDecisionRequest,
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    return WorkflowService(db).resume_run(tenant=tenant, run_id=run_id, payload=payload)
