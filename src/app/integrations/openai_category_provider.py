from time import perf_counter

from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import ProviderUnavailableError
from app.integrations.category_provider import CategoryProvider, CategorySuggestionResult
from app.schemas.agent import CategorySuggestionResponse, InvoiceFields
from app.schemas.common import UsageMetrics


class OpenAICategoryProvider(CategoryProvider):
    def suggest(self, *, fields: InvoiceFields, document_text: str) -> CategorySuggestionResult:
        if not settings.llm_api_key:
            raise ProviderUnavailableError("OPENAI provider selected but LLM_API_KEY is missing.")

        started = perf_counter()
        client = OpenAI(api_key=settings.llm_api_key)
        completion = client.chat.completions.parse(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "Suggest one finance category for the document. Keep the reason grounded and short.",
                },
                {"role": "user", "content": f"Fields: {fields.model_dump_json()}\nDocument excerpt: {document_text[:4000]}"},
            ],
            response_format=CategorySuggestionResponse,
        )
        parsed = completion.choices[0].message.parsed or CategorySuggestionResponse(
            category="general-expense",
            reason="fallback",
            source="openai",
            confidence=0.5,
        )
        usage = completion.usage
        return CategorySuggestionResult(
            suggestion=parsed,
            raw_response={"model": settings.llm_model},
            usage=UsageMetrics(
                provider="openai",
                model=settings.llm_model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                estimated_cost_usd=0,
                latency_ms=int((perf_counter() - started) * 1000),
            ),
        )
