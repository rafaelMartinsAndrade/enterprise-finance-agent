from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Supplier(Base, IdMixin, TimestampMixin):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("organization_id", "supplier_code", name="uq_suppliers_org_code"),
        UniqueConstraint("organization_id", "tax_id", name="uq_suppliers_org_tax_id"),
    )

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    supplier_code: Mapped[str] = mapped_column(String(40), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    tax_id: Mapped[str] = mapped_column(String(30), nullable=False)
    default_category: Mapped[str] = mapped_column(String(80), nullable=False, default="general")
    payment_terms_days: Mapped[int] = mapped_column(nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
