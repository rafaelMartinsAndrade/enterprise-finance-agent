from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class FinanceDocumentVersion(Base, IdMixin, TimestampMixin):
    __tablename__ = "finance_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_finance_document_versions_doc_version"),
    )

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("finance_documents.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(400), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded", index=True)
    page_count: Mapped[int] = mapped_column(nullable=False, default=0)
    character_count: Mapped[int] = mapped_column(nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
