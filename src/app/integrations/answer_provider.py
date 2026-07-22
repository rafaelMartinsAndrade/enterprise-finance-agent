from dataclasses import dataclass

from app.integrations.embedding_provider import ProviderUsage


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_title: str
    version_number: int
    page_number: int | None
    section_title: str | None
    content: str
    excerpt: str
    score: float


@dataclass(slots=True)
class AnswerGenerationResult:
    answer: str
    used_chunk_ids: list[int]
    has_sufficient_evidence: bool
    usage: ProviderUsage
    raw_response: dict


class AnswerProvider:
    def generate(self, *, question: str, chunks: list[RetrievedChunk]) -> AnswerGenerationResult:
        raise NotImplementedError
