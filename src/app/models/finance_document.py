from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class FinanceDocument(Base, IdMixin, TimestampMixin):
    __tablename__ = "finance_documents"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded", index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="upload")
    current_version_number: Mapped[int | None] = mapped_column(nullable=True)
    latest_run_id: Mapped[int | None] = mapped_column(nullable=True)
    latest_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
