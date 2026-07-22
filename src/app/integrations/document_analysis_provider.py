from dataclasses import dataclass

from app.schemas.agent import InvoiceFields
from app.schemas.common import UsageMetrics


@dataclass(slots=True)
class DocumentAnalysisResult:
    fields: InvoiceFields
    raw_response: dict
    usage: UsageMetrics


class DocumentAnalysisProvider:
    def analyze(self, *, text: str) -> DocumentAnalysisResult:
        raise NotImplementedError
