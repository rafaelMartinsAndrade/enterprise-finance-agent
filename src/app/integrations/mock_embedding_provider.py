import hashlib
import math
import re
import time
from decimal import Decimal

from app.core.config import settings
from app.integrations.embedding_provider import EmbeddingBatchResult, EmbeddingProvider, ProviderUsage


class MockEmbeddingProvider(EmbeddingProvider):
    token_pattern = re.compile(r"[a-z0-9]+", flags=re.IGNORECASE)

    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        start = time.perf_counter()
        vectors = [self._embed_text(text) for text in texts]
        input_tokens = sum(max(1, len(text) // 4) for text in texts)
        usage = ProviderUsage(
            provider="mock",
            model=settings.embedding_model,
            input_tokens=input_tokens,
            output_tokens=0,
            estimated_cost_usd=(Decimal(input_tokens) * Decimal("0.0000001")).quantize(
                Decimal("0.000001")
            ),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )
        return EmbeddingBatchResult(vectors=vectors, usage=usage)

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * settings.embedding_dimensions
        tokens = self.token_pattern.findall(text.lower())[:4096]
        if not tokens:
            return vector
        for offset, token in enumerate(tokens):
            digest = hashlib.sha256(f"{token}:{offset % 11}".encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % settings.embedding_dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
