from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(slots=True)
class ExtractedPage:
    page_number: int
    text: str
    section_title: str | None


@dataclass(slots=True)
class ExtractedDocument:
    text: str
    pages: list[ExtractedPage]
    metadata: dict


class TextExtractionService:
    def extract(self, *, storage_path: str, content_type: str) -> ExtractedDocument:
        path = Path(storage_path)
        if content_type == "application/pdf":
            return self._extract_pdf(path)
        return self._extract_text(path)

    def _extract_pdf(self, path: Path) -> ExtractedDocument:
        reader = PdfReader(str(path))
        pages: list[ExtractedPage] = []
        all_text: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            section_title = self._infer_section_title(text)
            pages.append(ExtractedPage(page_number=index, text=text, section_title=section_title))
            all_text.append(text)
        combined = "\n\n".join(all_text).strip()
        return ExtractedDocument(
            text=combined,
            pages=pages,
            metadata={"page_count": len(reader.pages), "format": "pdf"},
        )

    def _extract_text(self, path: Path) -> ExtractedDocument:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        section_title = self._infer_section_title(text)
        return ExtractedDocument(
            text=text,
            pages=[ExtractedPage(page_number=1, text=text, section_title=section_title)],
            metadata={"page_count": 1, "format": "text"},
        )

    def _infer_section_title(self, text: str) -> str | None:
        for raw_line in text.splitlines():
            line = raw_line.strip().strip("#").strip()
            if not line:
                continue
            if len(line) <= 90 and raw_line.strip().startswith("#"):
                return line
            if len(line) <= 90 and line == line.title():
                return line
        return None
