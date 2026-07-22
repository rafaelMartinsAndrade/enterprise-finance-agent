import sqlite3
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.core.config import settings
from app.core.exceptions import DomainValidationError, NotFoundError, ProcessingError
from app.integrations.provider_factory import build_document_analysis_provider
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.finance_repository import FinanceRepository
from app.repositories.llm_execution_repository import LLMExecutionRepository
from app.schemas.agent import (
    AgentRunListItem,
    AgentRunResponse,
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    CategorySuggestionResponse,
    ConfidenceBreakdownResponse,
    DraftPreEntryResponse,
    DuplicateMatchResponse,
    InvoiceFields,
    SupplierMatchResponse,
    ToolExecutionResponse,
    WorkflowStartResponse,
)
from app.schemas.auth import TenantContext
from app.schemas.common import AgentRunStatus, ApprovalStatus, DocumentStatus, UsageMetrics
from app.services.agent_tools_service import AgentToolsService, ToolContext
from app.services.text_extraction_service import TextExtractionService


class AgentState(TypedDict):
    agent_run_id: int
    organization_id: int
    user_id: int
    document_id: int
    version_id: int
    document_text: str
    content_type: str
    storage_path: str
    page_count: int
    character_count: int
    extraction_metadata: dict
    extracted_fields: dict
    supplier_match: dict
    duplicate_matches: list[dict]
    category_suggestion: dict
    confidence_breakdown: dict
    draft_pre_entry_id: int | None
    approval_decision: dict
    final_action: str | None
    current_node: str | None
    step_count: int
    alerts: list[str]


class WorkflowService:
    def __init__(self, session) -> None:
        self.session = session
        self.finance_repository = FinanceRepository(session)
        self.run_repository = AgentRunRepository(session)
        self.llm_repository = LLMExecutionRepository(session)
        self.extraction_service = TextExtractionService()
        self.tools_service = AgentToolsService(session)

    def get_existing_run_by_idempotency_key(
        self,
        *,
        tenant: TenantContext,
        idempotency_key: str,
    ):
        return self.run_repository.get_run_by_idempotency_key(
            organization_id=tenant.organization_id,
            idempotency_key=idempotency_key,
        )

    def list_runs(self, *, tenant: TenantContext) -> list[AgentRunListItem]:
        return [
            AgentRunListItem(
                id=item.id,
                document_id=item.document_id,
                thread_id=item.thread_id,
                status=AgentRunStatus(item.status),
                confidence_score=item.confidence_score,
                final_action=item.final_action,
            )
            for item in self.run_repository.list_runs(tenant.organization_id)
        ]

    def start_run(
        self,
        *,
        tenant: TenantContext,
        document_id: int,
        version_id: int,
        idempotency_key: str | None = None,
    ) -> WorkflowStartResponse:
        if idempotency_key:
            existing = self.run_repository.get_run_by_idempotency_key(
                organization_id=tenant.organization_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                return WorkflowStartResponse(
                    document_id=document_id,
                    version_id=version_id,
                    run=self.get_run(tenant=tenant, run_id=existing.id),
                )

        version = self.finance_repository.get_version(version_id)
        document = self.finance_repository.get_document(document_id)
        if version is None or document is None or document.organization_id != tenant.organization_id:
            raise NotFoundError("Document version not found for tenant.")

        run = self.run_repository.create_run(
            organization_id=tenant.organization_id,
            document_id=document_id,
            version_id=version_id,
            initiated_by_user_id=tenant.user_id,
            thread_id=str(uuid.uuid4())[:120],
            idempotency_key=idempotency_key,
        )
        self.finance_repository.update_document(
            document,
            status=DocumentStatus.analyzing.value,
            latest_run_id=run.id,
        )
        self.finance_repository.update_version(
            version,
            processing_status=DocumentStatus.analyzing.value,
        )
        try:
            self._execute_graph(
                tenant=tenant,
                run_id=run.id,
                initial_state=self._build_initial_state(
                    tenant=tenant,
                    run_id=run.id,
                    document_id=document.id,
                    version_id=version.id,
                    storage_path=version.storage_path,
                    content_type=version.content_type,
                ),
                resume_payload=None,
            )
        except Exception:
            pass
        return WorkflowStartResponse(
            document_id=document.id,
            version_id=version.id,
            run=self.get_run(tenant=tenant, run_id=run.id),
        )

    def resume_run(
        self,
        *,
        tenant: TenantContext,
        run_id: int,
        payload: ApprovalDecisionRequest,
    ) -> AgentRunResponse:
        run = self._get_tenant_run(tenant=tenant, run_id=run_id)
        if run.status != AgentRunStatus.waiting_approval.value:
            raise DomainValidationError("Only waiting approval runs can be resumed.")
        try:
            self._execute_graph(
                tenant=tenant,
                run_id=run.id,
                initial_state=None,
                resume_payload={
                    "action": payload.action.value,
                    "notes": payload.notes,
                    "edited_fields": None if payload.edited_fields is None else payload.edited_fields.model_dump(mode="json"),
                    "reviewed_by": tenant.user_email,
                },
            )
        except Exception:
            pass
        updated_run = self._get_tenant_run(tenant=tenant, run_id=run.id)
        approval = self.run_repository.get_latest_approval(run.id)
        if (
            approval is not None
            and approval.status == ApprovalStatus.pending.value
            and updated_run.status != AgentRunStatus.failed.value
        ):
            self.run_repository.resolve_approval(
                approval,
                status={
                    "approve": ApprovalStatus.approved.value,
                    "reject": ApprovalStatus.rejected.value,
                    "edit": ApprovalStatus.edited.value,
                }[payload.action.value],
                resolved_by_user_id=tenant.user_id,
                decision_notes=payload.notes,
                edited_fields_json={} if payload.edited_fields is None else payload.edited_fields.model_dump(mode="json"),
            )
        return self.get_run(tenant=tenant, run_id=run.id)

    def get_run(self, *, tenant: TenantContext, run_id: int) -> AgentRunResponse:
        run = self._get_tenant_run(tenant=tenant, run_id=run_id)
        state = run.state_json or {}
        approval = self.run_repository.get_latest_approval(run.id)
        draft = self.finance_repository.get_draft_by_run(run.id)
        tool_executions = self.run_repository.list_tool_executions(run.id)
        llm_usage = [
            UsageMetrics(
                provider=item.provider,
                model=item.model,
                input_tokens=item.input_tokens,
                output_tokens=item.output_tokens,
                estimated_cost_usd=Decimal(str(item.estimated_cost_usd)),
                latency_ms=item.latency_ms,
            )
            for item in self.llm_repository.list_by_run(run.id)
        ]
        return AgentRunResponse(
            id=run.id,
            document_id=run.document_id,
            version_id=run.version_id,
            thread_id=run.thread_id,
            status=AgentRunStatus(run.status),
            current_node=run.current_node,
            step_count=run.step_count,
            confidence_score=run.confidence_score,
            final_action=run.final_action,
            last_error_message=run.last_error_message,
            extracted_fields=InvoiceFields.model_validate(state.get("extracted_fields", {})),
            supplier_match=None if not state.get("supplier_match") else SupplierMatchResponse.model_validate(state["supplier_match"]),
            duplicate_matches=[DuplicateMatchResponse.model_validate(item) for item in state.get("duplicate_matches", [])],
            category_suggestion=None if not state.get("category_suggestion") else CategorySuggestionResponse.model_validate(state["category_suggestion"]),
            confidence_breakdown=None if not state.get("confidence_breakdown") else ConfidenceBreakdownResponse.model_validate(state["confidence_breakdown"]),
            approval_request=None
            if approval is None
            else ApprovalRequestResponse(
                id=approval.id,
                status=ApprovalStatus(approval.status),
                request_payload=approval.request_payload_json,
                decision_notes=approval.decision_notes,
                edited_fields=approval.edited_fields_json,
            ),
            draft_pre_entry=None
            if draft is None
            else DraftPreEntryResponse(
                id=draft.id,
                supplier_name=draft.supplier_name,
                document_number=draft.document_number,
                issue_date=draft.issue_date,
                due_date=draft.due_date,
                amount=Decimal(str(draft.amount)),
                currency=draft.currency,
                category=draft.category,
                description=draft.description,
                status=draft.status,
            ),
            tool_executions=[
                ToolExecutionResponse(
                    id=item.id,
                    tool_name=item.tool_name,
                    tool_type=item.tool_type,
                    status=item.status,
                    duration_ms=item.duration_ms,
                    arguments=item.arguments_json,
                    result=item.result_json,
                    error_message=item.error_message,
                )
                for item in tool_executions
            ],
            llm_usage=llm_usage,
        )

    def _get_tenant_run(self, *, tenant: TenantContext, run_id: int):
        run = self.run_repository.get_run(run_id)
        if run is None or run.organization_id != tenant.organization_id:
            raise NotFoundError("Agent run not found for tenant.")
        return run

    def _build_initial_state(
        self,
        *,
        tenant: TenantContext,
        run_id: int,
        document_id: int,
        version_id: int,
        storage_path: str,
        content_type: str,
    ) -> AgentState:
        extracted = self.extraction_service.extract(storage_path=storage_path, content_type=content_type)
        version = self.finance_repository.get_version(version_id)
        if version is not None:
            self.finance_repository.update_version(
                version,
                processing_status=DocumentStatus.analyzing.value,
                page_count=extracted.metadata.get("page_count", len(extracted.pages)),
                character_count=len(extracted.text),
                extraction_metadata_json=extracted.metadata,
            )
        return AgentState(
            agent_run_id=run_id,
            organization_id=tenant.organization_id,
            user_id=tenant.user_id,
            document_id=document_id,
            version_id=version_id,
            document_text=extracted.text,
            content_type=content_type,
            storage_path=storage_path,
            page_count=extracted.metadata.get("page_count", len(extracted.pages)),
            character_count=len(extracted.text),
            extraction_metadata=extracted.metadata,
            extracted_fields={},
            supplier_match={},
            duplicate_matches=[],
            category_suggestion={},
            confidence_breakdown={},
            draft_pre_entry_id=None,
            approval_decision={},
            final_action=None,
            current_node="extract_fields",
            step_count=0,
            alerts=[],
        )

    def _build_graph(self):
        Path(settings.agent_checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        checkpointer = SqliteSaver(sqlite3.connect(settings.agent_checkpoint_path, check_same_thread=False))
        builder = StateGraph(AgentState)
        builder.add_node("extract_fields", self._node_extract_fields)
        builder.add_node("supplier_lookup", self._node_supplier_lookup)
        builder.add_node("duplicate_check", self._node_duplicate_check)
        builder.add_node("categorize_document", self._node_categorize_document)
        builder.add_node("calculate_confidence", self._node_calculate_confidence)
        builder.add_node("create_draft", self._node_create_draft)
        builder.add_node("human_review", self._node_human_review)
        builder.add_node("approve_run", self._node_approve_run)
        builder.add_node("reject_run", self._node_reject_run)
        builder.add_edge(START, "extract_fields")
        builder.add_edge("extract_fields", "supplier_lookup")
        builder.add_edge("supplier_lookup", "duplicate_check")
        builder.add_edge("duplicate_check", "categorize_document")
        builder.add_edge("categorize_document", "calculate_confidence")
        builder.add_edge("calculate_confidence", "create_draft")
        builder.add_edge("create_draft", "human_review")
        builder.add_edge("approve_run", END)
        builder.add_edge("reject_run", END)
        return builder.compile(checkpointer=checkpointer)

    def _execute_graph(
        self,
        *,
        tenant: TenantContext,
        run_id: int,
        initial_state: AgentState | None,
        resume_payload: dict | None,
    ) -> None:
        run = self._get_tenant_run(tenant=tenant, run_id=run_id)
        graph = self._build_graph()
        config = {"configurable": {"thread_id": run.thread_id}}
        try:
            stream = (
                graph.stream_events(initial_state, config=config, version="v3")
                if resume_payload is None
                else graph.stream_events(Command(resume=resume_payload), config=config, version="v3")
            )
            _ = stream.output
            snapshot = graph.get_state(config)
            values = snapshot.values if snapshot is not None else (initial_state or {})
            confidence = float(values.get("confidence_breakdown", {}).get("final_score", 0.0) or 0.0)
            if stream.interrupted:
                self.run_repository.create_or_update_approval(
                    organization_id=tenant.organization_id,
                    agent_run_id=run.id,
                    requested_by_user_id=tenant.user_id,
                    request_payload_json=stream.interrupts[0].value,
                )
                self.run_repository.update_run(
                    run,
                    status=AgentRunStatus.waiting_approval.value,
                    current_node="human_review",
                    step_count=values.get("step_count", 0),
                    confidence_score=confidence,
                    final_action=values.get("final_action"),
                    state_json=values,
                    last_error_message=None,
                )
                self._sync_document_status(run=run, status=DocumentStatus.waiting_approval, state=values)
                return

            final_action = values.get("final_action")
            final_status = AgentRunStatus.approved if final_action == "approved" else AgentRunStatus.rejected
            self.run_repository.update_run(
                run,
                status=final_status.value,
                current_node=values.get("current_node"),
                step_count=values.get("step_count", 0),
                confidence_score=confidence,
                final_action=final_action,
                state_json=values,
                last_error_message=None,
            )
            self._sync_document_status(
                run=run,
                status=DocumentStatus.approved if final_status is AgentRunStatus.approved else DocumentStatus.rejected,
                state=values,
            )
        except Exception as exc:
            failure_state = run.state_json or initial_state or {}
            self.run_repository.update_run(
                run,
                status=AgentRunStatus.failed.value,
                current_node="failed",
                step_count=run.step_count,
                confidence_score=run.confidence_score,
                final_action="failed",
                state_json=failure_state,
                last_error_message=str(exc),
            )
            self._sync_document_status(run=run, status=DocumentStatus.failed, state=failure_state, error_message=str(exc))
            raise

    def _sync_document_status(
        self,
        *,
        run,
        status: DocumentStatus,
        state: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        document = self.finance_repository.get_document(run.document_id)
        version = self.finance_repository.get_version(run.version_id)
        if document is None or version is None:
            return
        state = state or {}
        self.finance_repository.update_document(
            document,
            status=status.value,
            latest_run_id=run.id,
            latest_error_message=error_message,
            current_version_number=version.version_number,
        )
        self.finance_repository.update_version(
            version,
            processing_status=status.value,
            page_count=state.get("page_count"),
            character_count=state.get("character_count"),
            error_message=error_message,
            extraction_metadata_json=state.get("extraction_metadata"),
            is_active=True,
        )
        self.finance_repository.deactivate_other_versions(document.id, version.id)

    def _ensure_step(self, state: AgentState, node_name: str) -> tuple[int, list[str]]:
        step_count = state.get("step_count", 0) + 1
        alerts = list(state.get("alerts", []))
        if step_count > settings.max_agent_steps:
            raise ProcessingError("Agent step limit exceeded.", details={"node": node_name})
        return step_count, alerts

    def _tool_context(self, state: AgentState) -> ToolContext:
        return ToolContext(
            organization_id=state["organization_id"],
            user_id=state["user_id"],
            agent_run_id=state["agent_run_id"],
            document_id=state["document_id"],
        )

    def _node_extract_fields(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "extract_fields")
        result = build_document_analysis_provider().analyze(text=state["document_text"])
        self.llm_repository.create(
            organization_id=state["organization_id"],
            user_id=state["user_id"],
            agent_run_id=state["agent_run_id"],
            document_id=state["document_id"],
            operation="extract_invoice_fields",
            provider=result.usage.provider,
            model=result.usage.model,
            status="succeeded",
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            estimated_cost_usd=result.usage.estimated_cost_usd,
            latency_ms=result.usage.latency_ms,
            request_payload_json={"document_id": state["document_id"]},
            response_payload_json=result.raw_response,
        )
        fields = result.fields
        if fields.amount is None:
            alerts.append("amount missing")
        if fields.document_number is None:
            alerts.append("document number missing")
        return {
            "agent_run_id": state["agent_run_id"],
            "extracted_fields": fields.model_dump(mode="json"),
            "current_node": "extract_fields",
            "step_count": step_count,
            "alerts": alerts,
        }

    def _node_supplier_lookup(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "supplier_lookup")
        fields = InvoiceFields.model_validate(state["extracted_fields"])
        match = self.tools_service.supplier_lookup(context=self._tool_context(state), fields=fields)
        if match.match_score < 0.7:
            alerts.append("supplier needs manual confirmation")
        return {
            "agent_run_id": state["agent_run_id"],
            "supplier_match": match.model_dump(mode="json"),
            "current_node": "supplier_lookup",
            "step_count": step_count,
            "alerts": alerts,
        }

    def _node_duplicate_check(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "duplicate_check")
        fields = InvoiceFields.model_validate(state["extracted_fields"])
        duplicates = self.tools_service.duplicate_check(context=self._tool_context(state), fields=fields)
        if duplicates:
            alerts.append("possible duplicate detected")
        return {
            "agent_run_id": state["agent_run_id"],
            "duplicate_matches": [item.model_dump(mode="json") for item in duplicates],
            "current_node": "duplicate_check",
            "step_count": step_count,
            "alerts": alerts,
        }

    def _node_categorize_document(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "categorize_document")
        fields = InvoiceFields.model_validate(state["extracted_fields"])
        suggestion = self.tools_service.categorize(
            context=self._tool_context(state),
            fields=fields,
            document_text=state["document_text"],
        )
        return {
            "agent_run_id": state["agent_run_id"],
            "category_suggestion": suggestion.model_dump(mode="json"),
            "current_node": "categorize_document",
            "step_count": step_count,
            "alerts": alerts,
        }

    def _node_calculate_confidence(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "calculate_confidence")
        fields = InvoiceFields.model_validate(state["extracted_fields"])
        supplier = SupplierMatchResponse.model_validate(state.get("supplier_match", {}))
        category = CategorySuggestionResponse.model_validate(state["category_suggestion"])
        duplicates = [DuplicateMatchResponse.model_validate(item) for item in state.get("duplicate_matches", [])]
        extraction_quality = sum(
            1
            for value in [
                fields.supplier_name,
                fields.document_number,
                fields.issue_date,
                fields.due_date,
                fields.amount,
                fields.description,
            ]
            if value
        ) / 6
        duplicate_penalty = min(0.5, max((item.match_score for item in duplicates), default=0.0))
        final_score = max(
            0.0,
            min(
                1.0,
                (extraction_quality * 0.35)
                + (supplier.match_score * 0.30)
                + (category.confidence * 0.20)
                + ((1 - duplicate_penalty) * 0.15),
            ),
        )
        return {
            "agent_run_id": state["agent_run_id"],
            "confidence_breakdown": {
                "extraction_quality": round(extraction_quality, 4),
                "supplier_match": round(supplier.match_score, 4),
                "duplicate_penalty": round(duplicate_penalty, 4),
                "category_confidence": round(category.confidence, 4),
                "final_score": round(final_score, 4),
                "alerts": alerts,
            },
            "current_node": "calculate_confidence",
            "step_count": step_count,
            "alerts": alerts,
        }

    def _node_create_draft(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "create_draft")
        fields = InvoiceFields.model_validate(state["extracted_fields"])
        supplier = SupplierMatchResponse.model_validate(state.get("supplier_match", {}))
        category = CategorySuggestionResponse.model_validate(state["category_suggestion"])
        draft = self.tools_service.create_draft(
            context=self._tool_context(state),
            fields=fields,
            category=category.category,
            supplier_id=supplier.supplier_id,
        )
        return {
            "agent_run_id": state["agent_run_id"],
            "draft_pre_entry_id": draft.id,
            "current_node": "human_review_pending",
            "step_count": step_count,
            "alerts": alerts,
        }

    def _node_human_review(self, state: AgentState):
        confidence = state["confidence_breakdown"]["final_score"]
        recommended_action = "approve" if confidence >= settings.confidence_approval_threshold and not state.get("duplicate_matches") else "edit"
        decision = interrupt(
            {
                "question": "Approve, reject, or edit this finance draft?",
                "recommended_action": recommended_action,
                "confidence_score": confidence,
                "alerts": state.get("alerts", []),
                "extracted_fields": state["extracted_fields"],
                "supplier_match": state.get("supplier_match", {}),
                "duplicate_matches": state.get("duplicate_matches", []),
                "category_suggestion": state.get("category_suggestion", {}),
                "draft_pre_entry_id": state.get("draft_pre_entry_id"),
            }
        )
        action = (decision or {}).get("action", "reject")
        if action == "approve":
            return Command(goto="approve_run", update={"approval_decision": decision})
        if action == "edit":
            return Command(goto="approve_run", update={"approval_decision": decision})
        return Command(goto="reject_run", update={"approval_decision": decision})

    def _node_approve_run(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "approve_run")
        decision = state.get("approval_decision", {})
        edited_fields = decision.get("edited_fields") or {}
        if edited_fields:
            merged = {**state["extracted_fields"], **{k: v for k, v in edited_fields.items() if v not in (None, "")}}
            fields = InvoiceFields.model_validate(merged)
            category = CategorySuggestionResponse.model_validate(state["category_suggestion"])
            supplier = SupplierMatchResponse.model_validate(state.get("supplier_match", {}))
            self.tools_service.create_draft(
                context=self._tool_context(state),
                fields=fields,
                category=category.category,
                supplier_id=supplier.supplier_id,
            )
            return {
                "agent_run_id": state["agent_run_id"],
                "extracted_fields": fields.model_dump(mode="json"),
                "final_action": "approved",
                "current_node": "approve_run",
                "step_count": step_count,
                "alerts": alerts,
            }
        return {
            "agent_run_id": state["agent_run_id"],
            "final_action": "approved",
            "current_node": "approve_run",
            "step_count": step_count,
            "alerts": alerts,
        }

    def _node_reject_run(self, state: AgentState) -> dict[str, Any]:
        step_count, alerts = self._ensure_step(state, "reject_run")
        draft = self.finance_repository.get_draft_by_run(state["agent_run_id"])
        if draft is not None:
            draft.status = "rejected"
            self.session.add(draft)
            self.session.commit()
        return {
            "agent_run_id": state["agent_run_id"],
            "final_action": "rejected",
            "current_node": "reject_run",
            "step_count": step_count,
            "alerts": alerts,
        }
