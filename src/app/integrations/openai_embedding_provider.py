import time
from decimal import Decimal

from app.core.config import settings
from app.core.exceptions import ProviderUnavailableError
from app.integrations.embedding_provider import EmbeddingBatchResult, EmbeddingProvider, ProviderUsage


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        if not settings.llm_api_key:
            raise ProviderUnavailableError("OPENAI embedding provider selected but LLM_API_KEY is missing.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailableError("openai package is not installed.") from exc

        client = OpenAI(api_key=settings.llm_api_key)
        start = time.perf_counter()
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        usage_obj = response.usage
        usage = ProviderUsage(
            provider="openai",
            model=settings.embedding_model,
            input_tokens=usage_obj.prompt_tokens if usage_obj else 0,
            output_tokens=0,
            estimated_cost_usd=Decimal("0"),
            latency_ms=elapsed_ms,
        )
        return EmbeddingBatchResult(
            vectors=[item.embedding for item in response.data],
            usage=usage,
        )
