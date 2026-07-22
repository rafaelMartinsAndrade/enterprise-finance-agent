from sqlalchemy import or_

from app.models.supplier import Supplier
from app.repositories.base import Repository


class SupplierRepository(Repository):
    def create(
        self,
        *,
        organization_id: int,
        supplier_code: str,
        legal_name: str,
        tax_id: str,
        default_category: str,
        payment_terms_days: int = 30,
        status: str = "active",
    ) -> Supplier:
        record = Supplier(
            organization_id=organization_id,
            supplier_code=supplier_code,
            legal_name=legal_name,
            tax_id=tax_id,
            default_category=default_category,
            payment_terms_days=payment_terms_days,
            status=status,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def list_by_organization(self, organization_id: int) -> list[Supplier]:
        return (
            self.session.query(Supplier)
            .filter(Supplier.organization_id == organization_id)
            .order_by(Supplier.legal_name.asc())
            .all()
        )

    def find_candidates(self, *, organization_id: int, supplier_name: str | None, tax_id: str | None) -> list[Supplier]:
        query = self.session.query(Supplier).filter(Supplier.organization_id == organization_id)
        conditions = []
        if tax_id:
            conditions.append(Supplier.tax_id == tax_id)
        if supplier_name:
            conditions.append(Supplier.legal_name.ilike(f"%{supplier_name}%"))
        if not conditions:
            return []
        return query.filter(or_(*conditions)).order_by(Supplier.legal_name.asc()).all()
