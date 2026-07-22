from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter, sleep

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import DomainValidationError, ProviderTimeoutError, RetryableToolError
from app.integrations.provider_factory import build_category_provider
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.finance_repository import FinanceRepository
from app.repositories.llm_execution_repository import LLMExecutionRepository
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.agent import CategorySuggestionResponse, DuplicateMatchResponse, InvoiceFields, SupplierMatchResponse


@dataclass(slots=True)
class ToolContext:
    organization_id: int
    user_id: int
    agent_run_id: int
    document_id: int


class SupplierLookupArgs(BaseModel):
    supplier_name: str | None = Field(default=None, max_length=180)
    supplier_tax_id: str | None = Field(default=None, max_length=30)


class DuplicateCheckArgs(BaseModel):
    supplier_name: str | None = Field(default=None, max_length=180)
    document_number: str | None = Field(default=None, max_length=80)
    amount: Decimal | None = Field(default=None, ge=0)


class DraftCreateArgs(BaseModel):
    supplier_id: int | None = None
    supplier_name: str = Field(min_length=2, max_length=180)
    document_number: str = Field(min_length=2, max_length=80)
    issue_date: str | None = Field(default=None, max_length=20)
    due_date: str | None = Field(default=None, max_length=20)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=10)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=2, max_length=240)


class AgentToolsService:
    def __init__(self, session) -> None:
        self.session = session
        self.supplier_repository = SupplierRepository(session)
        self.finance_repository = FinanceRepository(session)
        self.run_repository = AgentRunRepository(session)
        self.llm_repository = LLMExecutionRepository(session)

    def supplier_lookup(self, *, context: ToolContext, fields: InvoiceFields) -> SupplierMatchResponse:
        args = SupplierLookupArgs(
            supplier_name=fields.supplier_name,
            supplier_tax_id=fields.supplier_tax_id,
        )
        return self._execute(
            context=context,
            tool_name="supplier_lookup",
            arguments=args.model_dump(mode="json"),
            fn=lambda: self._supplier_lookup_impl(context=context, args=args),
        )

    def duplicate_check(self, *, context: ToolContext, fields: InvoiceFields) -> list[DuplicateMatchResponse]:
        args = DuplicateCheckArgs(
            supplier_name=fields.supplier_name,
            document_number=fields.document_number,
            amount=fields.amount,
        )
        return self._execute(
            context=context,
            tool_name="duplicate_check",
            arguments=args.model_dump(mode="json"),
            fn=lambda: self._duplicate_check_impl(context=context, args=args),
        )

    def categorize(self, *, context: ToolContext, fields: InvoiceFields, document_text: str) -> CategorySuggestionResponse:
        result = self._execute(
            context=context,
            tool_name="categorize_document",
            arguments={"fields": fields.model_dump(mode="json"), "document_excerpt": document_text[:500]},
            fn=lambda: self._categorize_impl(context=context, fields=fields, document_text=document_text),
        )
        return result

    def create_draft(self, *, context: ToolContext, fields: InvoiceFields, category: str, supplier_id: int | None):
        args = DraftCreateArgs(
            supplier_id=supplier_id,
            supplier_name=fields.supplier_name or "Unknown supplier",
            document_number=fields.document_number or f"DOC-{context.document_id}",
            issue_date=fields.issue_date,
            due_date=fields.due_date,
            amount=fields.amount or Decimal("0"),
            currency=fields.currency,
            category=category,
            description=fields.description or "Finance draft created by agent",
        )
        return self._execute(
            context=context,
            tool_name="create_draft_pre_entry",
            arguments=args.model_dump(mode="json"),
            fn=lambda: self._create_draft_impl(context=context, args=args),
        )

    def _execute(self, *, context: ToolContext, tool_name: str, arguments: dict, fn):
        attempts = 0
        started = perf_counter()
        last_error: Exception | None = None
        while attempts <= settings.tool_max_retries:
            attempts += 1
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(fn)
                    result = future.result(timeout=settings.tool_timeout_seconds)
                self.run_repository.create_tool_execution(
                    organization_id=context.organization_id,
                    agent_run_id=context.agent_run_id,
                    tool_name=tool_name,
                    tool_type="internal",
                    status="succeeded",
                    duration_ms=int((perf_counter() - started) * 1000),
                    arguments_json={**arguments, "attempts": attempts},
                    result_json=self._serialize_result(result),
                )
                return result
            except FuturesTimeoutError:
                self.session.rollback()
                last_error = ProviderTimeoutError(f"Tool {tool_name} exceeded timeout.")
            except RetryableToolError as exc:
                self.session.rollback()
                last_error = exc
            except Exception as exc:
                self.session.rollback()
                last_error = exc
                break
            if attempts <= settings.tool_max_retries:
                sleep(0.05 * attempts)

        error_message = str(last_error or "Unknown tool failure.")
        self.run_repository.create_tool_execution(
            organization_id=context.organization_id,
            agent_run_id=context.agent_run_id,
            tool_name=tool_name,
            tool_type="internal",
            status="failed",
            duration_ms=int((perf_counter() - started) * 1000),
            arguments_json={**arguments, "attempts": attempts},
            result_json={},
            error_message=error_message,
        )
        if isinstance(last_error, Exception):
            raise last_error
        raise DomainValidationError(error_message)

    def _supplier_lookup_impl(self, *, context: ToolContext, args: SupplierLookupArgs) -> SupplierMatchResponse:
        if args.supplier_name is None and args.supplier_tax_id is None:
            raise DomainValidationError("Supplier lookup requires supplier name or tax id.")
        if args.supplier_name and "retry-me" in args.supplier_name.lower():
            raise RetryableToolError("Transient supplier registry failure.")
        candidates = self.supplier_repository.find_candidates(
            organization_id=context.organization_id,
            supplier_name=args.supplier_name,
            tax_id=args.supplier_tax_id,
        )
        if not candidates:
            return SupplierMatchResponse(match_score=0.0, match_reason="supplier not found", ambiguous=False)
        if len(candidates) > 1:
            best = candidates[0]
            return SupplierMatchResponse(
                supplier_id=best.id,
                supplier_code=best.supplier_code,
                legal_name=best.legal_name,
                tax_id=best.tax_id,
                match_score=0.6,
                match_reason="multiple candidates found, manual confirmation required",
                ambiguous=True,
            )
        supplier = candidates[0]
        exact_tax = bool(args.supplier_tax_id and args.supplier_tax_id == supplier.tax_id)
        return SupplierMatchResponse(
            supplier_id=supplier.id,
            supplier_code=supplier.supplier_code,
            legal_name=supplier.legal_name,
            tax_id=supplier.tax_id,
            match_score=1.0 if exact_tax else 0.88,
            match_reason="matched by tax id" if exact_tax else "matched by legal name",
            ambiguous=False,
        )

    def _duplicate_check_impl(self, *, context: ToolContext, args: DuplicateCheckArgs) -> list[DuplicateMatchResponse]:
        if args.document_number is None and args.amount is None:
            return []
        drafts = self.finance_repository.find_duplicate_drafts(
            organization_id=context.organization_id,
            supplier_name=args.supplier_name,
            document_number=args.document_number,
            amount=float(args.amount) if args.amount is not None else None,
        )
        matches: list[DuplicateMatchResponse] = []
        for draft in drafts:
            score = 0.0
            reasons: list[str] = []
            if args.document_number and draft.document_number == args.document_number:
                score += 0.5
                reasons.append("same document number")
            if args.amount is not None and Decimal(str(draft.amount)) == args.amount:
                score += 0.3
                reasons.append("same amount")
            if args.supplier_name and args.supplier_name.lower() in draft.supplier_name.lower():
                score += 0.2
                reasons.append("same supplier")
            if score >= 0.4:
                matches.append(
                    DuplicateMatchResponse(
                        draft_id=draft.id,
                        supplier_name=draft.supplier_name,
                        document_number=draft.document_number,
                        amount=Decimal(str(draft.amount)),
                        match_score=min(score, 1.0),
                        reason=", ".join(reasons),
                    )
                )
        return matches

    def _categorize_impl(self, *, context: ToolContext, fields: InvoiceFields, document_text: str) -> CategorySuggestionResponse:
        result = build_category_provider().suggest(fields=fields, document_text=document_text)
        self.llm_repository.create(
            organization_id=context.organization_id,
            user_id=context.user_id,
            agent_run_id=context.agent_run_id,
            document_id=context.document_id,
            operation="categorize_document",
            provider=result.usage.provider,
            model=result.usage.model,
            status="succeeded",
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            estimated_cost_usd=result.usage.estimated_cost_usd,
            latency_ms=result.usage.latency_ms,
            request_payload_json={"fields": fields.model_dump(mode="json")},
            response_payload_json=result.raw_response,
        )
        return result.suggestion

    def _create_draft_impl(self, *, context: ToolContext, args: DraftCreateArgs):
        return self.finance_repository.create_or_update_draft(
            organization_id=context.organization_id,
            agent_run_id=context.agent_run_id,
            supplier_id=args.supplier_id,
            supplier_name=args.supplier_name,
            document_number=args.document_number,
            issue_date=args.issue_date,
            due_date=args.due_date,
            amount=float(args.amount),
            currency=args.currency,
            category=args.category,
            description=args.description,
            status="draft",
            payload_json=args.model_dump(mode="json"),
        )

    def _serialize_result(self, result):
        if isinstance(result, Decimal):
            return str(result)
        if isinstance(result, (datetime, date)):
            return result.isoformat()
        if isinstance(result, dict):
            return {key: self._serialize_result(value) for key, value in result.items()}
        if isinstance(result, list):
            return [self._serialize_result(item) for item in result]
        if hasattr(result, "model_dump"):
            return self._serialize_result(result.model_dump(mode="json"))
        if hasattr(result, "__table__"):
            return {
                column.name: self._serialize_result(getattr(result, column.name))
                for column in result.__table__.columns
            }
        if hasattr(result, "__dict__"):
            return {
                key: self._serialize_result(value)
                for key, value in result.__dict__.items()
                if not key.startswith("_")
            }
        return {"value": str(result)}
