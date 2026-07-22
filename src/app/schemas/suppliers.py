from app.schemas.common import AppBaseModel


class SupplierResponse(AppBaseModel):
    id: int
    supplier_code: str
    legal_name: str
    tax_id: str
    default_category: str
    payment_terms_days: int
    status: str
