from app.repositories.supplier_repository import SupplierRepository
from app.schemas.suppliers import SupplierResponse


class SupplierService:
    def __init__(self, session) -> None:
        self.repository = SupplierRepository(session)

    def list_suppliers(self, organization_id: int) -> list[SupplierResponse]:
        return [
            SupplierResponse(
                id=item.id,
                supplier_code=item.supplier_code,
                legal_name=item.legal_name,
                tax_id=item.tax_id,
                default_category=item.default_category,
                payment_terms_days=item.payment_terms_days,
                status=item.status,
            )
            for item in self.repository.list_by_organization(organization_id)
        ]
