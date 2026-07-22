import re
import time
from decimal import Decimal

from app.core.config import settings
from app.integrations.answer_provider import AnswerGenerationResult, AnswerProvider, RetrievedChunk
from app.integrations.embedding_provider import ProviderUsage


class MockAnswerProvider(AnswerProvider):
    def generate(self, *, question: str, chunks: list[RetrievedChunk]) -> AnswerGenerationResult:
        start = time.perf_counter()
        if not chunks:
            return AnswerGenerationResult(
                answer="I could not find enough evidence in current organization knowledge base.",
                used_chunk_ids=[],
                has_sufficient_evidence=False,
                usage=ProviderUsage(
                    provider="mock",
                    model=settings.llm_model,
                    input_tokens=max(1, len(question) // 4),
                    output_tokens=14,
                    estimated_cost_usd=Decimal("0.000001"),
                    latency_ms=int((time.perf_counter() - start) * 1000),
                ),
                raw_response={"mode": "no_evidence"},
            )

        snippets: list[str] = []
        used_ids: list[int] = []
        question_terms = {term for term in re.findall(r"[a-z0-9]+", question.lower()) if len(term) > 2}
        for chunk in chunks[:3]:
            sentences = re.split(r"(?<=[.!?])\s+", chunk.content.strip())
            best_sentence = next(
                (
                    sentence
                    for sentence in sentences
                    if question_terms.intersection(re.findall(r"[a-z0-9]+", sentence.lower()))
                ),
                sentences[0] if sentences and sentences[0] else chunk.excerpt,
            )
            snippets.append(best_sentence.strip())
            used_ids.append(chunk.chunk_id)

        answer = "Based on retrieved evidence: " + " ".join(snippets)
        usage = ProviderUsage(
            provider="mock",
            model=settings.llm_model,
            input_tokens=max(1, (len(question) + sum(len(chunk.content) for chunk in chunks[:3])) // 4),
            output_tokens=max(20, len(answer) // 5),
            estimated_cost_usd=Decimal("0.000004"),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )
        return AnswerGenerationResult(
            answer=answer,
            used_chunk_ids=used_ids,
            has_sufficient_evidence=True,
            usage=usage,
            raw_response={"mode": "extractive_template"},
        )
