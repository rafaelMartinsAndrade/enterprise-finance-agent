from time import perf_counter

from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import ProviderUnavailableError
from app.integrations.document_analysis_provider import DocumentAnalysisProvider, DocumentAnalysisResult
from app.schemas.agent import InvoiceFields
from app.schemas.common import UsageMetrics


class OpenAIDocumentAnalysisProvider(DocumentAnalysisProvider):
    def analyze(self, *, text: str) -> DocumentAnalysisResult:
        if not settings.llm_api_key:
            raise ProviderUnavailableError("OPENAI provider selected but LLM_API_KEY is missing.")

        started = perf_counter()
        client = OpenAI(api_key=settings.llm_api_key)
        completion = client.chat.completions.parse(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract invoice-like finance document fields. "
                        "Return only supported fields. Use ISO dates when possible."
                    ),
                },
                {"role": "user", "content": text[:12000]},
            ],
            response_format=InvoiceFields,
        )
        parsed = completion.choices[0].message.parsed or InvoiceFields()
        usage = completion.usage
        return DocumentAnalysisResult(
            fields=parsed,
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
