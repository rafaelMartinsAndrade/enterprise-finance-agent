from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.common import (
    AgentRunStatus,
    AppBaseModel,
    ApprovalAction,
    ApprovalStatus,
    DocumentStatus,
    ToolExecutionStatus,
    UsageMetrics,
)


class InvoiceFields(AppBaseModel):
    supplier_name: str | None = Field(default=None, max_length=180)
    supplier_tax_id: str | None = Field(default=None, max_length=30)
    document_number: str | None = Field(default=None, max_length=80)
    issue_date: str | None = Field(default=None, max_length=20)
    due_date: str | None = Field(default=None, max_length=20)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=10)
    description: str | None = Field(default=None, max_length=240)


class SupplierMatchResponse(AppBaseModel):
    supplier_id: int | None = None
    supplier_code: str | None = None
    legal_name: str | None = None
    tax_id: str | None = None
    match_score: float = Field(ge=0, le=1)
    match_reason: str
    ambiguous: bool = False


class DuplicateMatchResponse(AppBaseModel):
    draft_id: int
    supplier_name: str
    document_number: str
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    match_score: float = Field(ge=0, le=1)
    reason: str


class CategorySuggestionResponse(AppBaseModel):
    category: str
    reason: str
    source: str
    confidence: float = Field(ge=0, le=1)


class ConfidenceBreakdownResponse(AppBaseModel):
    extraction_quality: float = Field(ge=0, le=1)
    supplier_match: float = Field(ge=0, le=1)
    duplicate_penalty: float = Field(ge=0, le=1)
    category_confidence: float = Field(ge=0, le=1)
    final_score: float = Field(ge=0, le=1)
    alerts: list[str]


class DraftPreEntryResponse(AppBaseModel):
    id: int
    supplier_name: str
    document_number: str
    issue_date: str | None
    due_date: str | None
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str
    category: str
    description: str
    status: str


class ToolExecutionResponse(AppBaseModel):
    id: int
    tool_name: str
    tool_type: str
    status: ToolExecutionStatus
    duration_ms: int = Field(ge=0)
    arguments: dict
    result: dict | list[dict]
    error_message: str | None


class ApprovalRequestResponse(AppBaseModel):
    id: int
    status: ApprovalStatus
    request_payload: dict
    decision_notes: str | None
    edited_fields: dict


class AgentRunResponse(AppBaseModel):
    id: int
    document_id: int
    version_id: int
    thread_id: str
    status: AgentRunStatus
    current_node: str | None
    step_count: int
    confidence_score: float = Field(ge=0, le=1)
    final_action: str | None
    last_error_message: str | None
    extracted_fields: InvoiceFields
    supplier_match: SupplierMatchResponse | None
    duplicate_matches: list[DuplicateMatchResponse]
    category_suggestion: CategorySuggestionResponse | None
    confidence_breakdown: ConfidenceBreakdownResponse | None
    approval_request: ApprovalRequestResponse | None
    draft_pre_entry: DraftPreEntryResponse | None
    tool_executions: list[ToolExecutionResponse]
    llm_usage: list[UsageMetrics]


class ApprovalDecisionRequest(AppBaseModel):
    action: ApprovalAction
    notes: str | None = Field(default=None, max_length=500)
    edited_fields: InvoiceFields | None = None

    @model_validator(mode="after")
    def validate_edit_payload(self):
        if self.action is ApprovalAction.edit and self.edited_fields is None:
            raise ValueError("edited_fields is required for edit actions.")
        return self


class AgentRunListItem(AppBaseModel):
    id: int
    document_id: int
    thread_id: str
    status: AgentRunStatus
    confidence_score: float = Field(ge=0, le=1)
    final_action: str | None


class WorkflowStartResponse(AppBaseModel):
    document_id: int
    version_id: int
    run: AgentRunResponse


class WorkflowSummaryResponse(AppBaseModel):
    document_status: DocumentStatus
    run_status: AgentRunStatus
    requires_approval: bool
