from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class ProviderUsage:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    latency_ms: int


@dataclass(slots=True)
class EmbeddingBatchResult:
    vectors: list[list[float]]
    usage: ProviderUsage


class EmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        raise NotImplementedError
