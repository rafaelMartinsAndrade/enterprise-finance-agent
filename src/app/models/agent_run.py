from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class AgentRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("finance_documents.id"), nullable=False, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("finance_document_versions.id"), nullable=False, index=True)
    initiated_by_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running", index=True)
    current_node: Mapped[str | None] = mapped_column(String(80), nullable=True)
    step_count: Mapped[int] = mapped_column(nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    final_action: Mapped[str | None] = mapped_column(String(40), nullable=True)
    state_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
