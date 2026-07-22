from decimal import Decimal

from app.integrations.category_provider import CategoryProvider, CategorySuggestionResult
from app.schemas.agent import CategorySuggestionResponse, InvoiceFields
from app.schemas.common import UsageMetrics


class MockCategoryProvider(CategoryProvider):
    rules = {
        "aws": "cloud",
        "hosting": "cloud",
        "internet": "telecom",
        "office": "office",
        "notebook": "hardware",
        "consulting": "professional-services",
        "salary": "payroll",
        "tax": "taxes",
    }

    def suggest(self, *, fields: InvoiceFields, document_text: str) -> CategorySuggestionResult:
        haystack = f"{fields.description or ''} {document_text}".lower()
        for term, category in self.rules.items():
            if term in haystack:
                return CategorySuggestionResult(
                    suggestion=CategorySuggestionResponse(
                        category=category,
                        reason=f"matched keyword '{term}'",
                        source="rules",
                        confidence=0.82,
                    ),
                    raw_response={"matched_term": term},
                    usage=UsageMetrics(
                        provider="mock",
                        model="mock-category-v1",
                        input_tokens=max(1, len(haystack) // 4),
                        output_tokens=12,
                        estimated_cost_usd=Decimal("0"),
                        latency_ms=5,
                    ),
                )
        return CategorySuggestionResult(
            suggestion=CategorySuggestionResponse(
                category="general-expense",
                reason="fallback default category",
                source="fallback",
                confidence=0.55,
            ),
            raw_response={"matched_term": None},
            usage=UsageMetrics(
                provider="mock",
                model="mock-category-v1",
                input_tokens=max(1, len(haystack) // 4),
                output_tokens=12,
                estimated_cost_usd=Decimal("0"),
                latency_ms=5,
            ),
        )
