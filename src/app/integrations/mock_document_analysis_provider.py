import re
from decimal import Decimal

from app.integrations.document_analysis_provider import DocumentAnalysisProvider, DocumentAnalysisResult
from app.schemas.agent import InvoiceFields
from app.schemas.common import UsageMetrics


class MockDocumentAnalysisProvider(DocumentAnalysisProvider):
    amount_pattern = re.compile(r"(?:^|\n)\s*(?:amount|valor)\s*:\s*([0-9]+(?:[.,][0-9]{2})?)", flags=re.IGNORECASE)
    supplier_pattern = re.compile(r"(?:^|\n)\s*(?:supplier|fornecedor)\s*:\s*(.+)", flags=re.IGNORECASE)
    tax_id_pattern = re.compile(r"(?:^|\n)\s*(?:tax id|cnpj|cpf)\s*:\s*([0-9./-]+)", flags=re.IGNORECASE)
    document_pattern = re.compile(r"(?:^|\n)\s*(?:invoice|nota|document)\s*:\s*([A-Za-z0-9-]+)", flags=re.IGNORECASE)
    issue_pattern = re.compile(r"(?:^|\n)\s*(?:issue date|emissao)\s*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", flags=re.IGNORECASE)
    due_pattern = re.compile(r"(?:^|\n)\s*(?:due date|vencimento)\s*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", flags=re.IGNORECASE)

    def analyze(self, *, text: str) -> DocumentAnalysisResult:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        supplier_name = self._search(self.supplier_pattern, text) or (lines[0] if lines else None)
        amount_raw = self._search(self.amount_pattern, text)
        amount = None if amount_raw is None else Decimal(self._normalize_amount(amount_raw))
        fields = InvoiceFields(
            supplier_name=supplier_name,
            supplier_tax_id=self._search(self.tax_id_pattern, text),
            document_number=self._search(self.document_pattern, text),
            issue_date=self._search(self.issue_pattern, text),
            due_date=self._search(self.due_pattern, text),
            amount=amount,
            currency="BRL",
            description=lines[1][:240] if len(lines) > 1 else (lines[0][:240] if lines else None),
        )
        return DocumentAnalysisResult(
            fields=fields,
            raw_response={"provider": "mock", "line_count": len(lines)},
            usage=UsageMetrics(
                provider="mock",
                model="mock-document-analysis-v1",
                input_tokens=max(1, len(text) // 4),
                output_tokens=40,
                estimated_cost_usd=Decimal("0"),
                latency_ms=20,
            ),
        )

    def _search(self, pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        if match is None:
            return None
        return match.group(1).strip()

    def _normalize_amount(self, raw_amount: str) -> str:
        normalized = raw_amount.strip().replace(" ", "")
        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                return normalized.replace(".", "").replace(",", ".")
            return normalized.replace(",", "")
        if "," in normalized:
            return normalized.replace(".", "").replace(",", ".")
        return normalized
