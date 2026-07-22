import json
import time
from decimal import Decimal

from app.core.config import settings
from app.core.exceptions import ProviderTimeoutError, ProviderUnavailableError
from app.integrations.answer_provider import AnswerGenerationResult, AnswerProvider, RetrievedChunk
from app.integrations.embedding_provider import ProviderUsage


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "used_chunk_ids": {"type": "array", "items": {"type": "integer"}},
        "has_sufficient_evidence": {"type": "boolean"},
    },
    "required": ["answer", "used_chunk_ids", "has_sufficient_evidence"],
    "additionalProperties": False,
}


class OpenAIAnswerProvider(AnswerProvider):
    def generate(self, *, question: str, chunks: list[RetrievedChunk]) -> AnswerGenerationResult:
        if not settings.llm_api_key:
            raise ProviderUnavailableError("OPENAI answer provider selected but LLM_API_KEY is missing.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailableError("openai package is not installed.") from exc

        client = OpenAI(api_key=settings.llm_api_key)
        context_lines = []
        for chunk in chunks:
            context_lines.append(
                (
                    f"chunk_id={chunk.chunk_id} | document={chunk.document_title} | "
                    f"version={chunk.version_number} | page={chunk.page_number} | "
                    f"section={chunk.section_title or '-'}\n{chunk.content}"
                )
            )

        start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Answer only with grounded evidence from retrieved chunks. "
                            "If evidence is weak, say so and set has_sufficient_evidence false."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question:\n{question}\n\n"
                            f"Retrieved chunks:\n\n" + "\n\n".join(context_lines)
                        ),
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "rag_answer",
                        "strict": True,
                        "schema": ANSWER_SCHEMA,
                    },
                },
            )
        except Exception as exc:
            if "timeout" in str(exc).lower():
                raise ProviderTimeoutError("OpenAI answer generation timed out.") from exc
            raise ProviderUnavailableError("OpenAI answer generation failed.") from exc

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        payload = json.loads(response.choices[0].message.content or "{}")
        usage_obj = response.usage
        usage = ProviderUsage(
            provider="openai",
            model=response.model,
            input_tokens=usage_obj.prompt_tokens if usage_obj else 0,
            output_tokens=usage_obj.completion_tokens if usage_obj else 0,
            estimated_cost_usd=Decimal("0"),
            latency_ms=elapsed_ms,
        )
        return AnswerGenerationResult(
            answer=payload["answer"],
            used_chunk_ids=payload["used_chunk_ids"],
            has_sufficient_evidence=payload["has_sufficient_evidence"],
            usage=usage,
            raw_response=payload,
        )
