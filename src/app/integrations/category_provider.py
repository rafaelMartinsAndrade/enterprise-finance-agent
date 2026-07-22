from dataclasses import dataclass

from app.schemas.agent import CategorySuggestionResponse, InvoiceFields
from app.schemas.common import UsageMetrics


@dataclass(slots=True)
class CategorySuggestionResult:
    suggestion: CategorySuggestionResponse
    raw_response: dict
    usage: UsageMetrics


class CategoryProvider:
    def suggest(self, *, fields: InvoiceFields, document_text: str) -> CategorySuggestionResult:
        raise NotImplementedError
