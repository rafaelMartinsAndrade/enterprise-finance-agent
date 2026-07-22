from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_tenant_context
from app.core.db import get_db
from app.schemas.auth import TenantContext
from app.schemas.suppliers import SupplierResponse
from app.services.supplier_service import SupplierService


router = APIRouter()


@router.get("", response_model=list[SupplierResponse], summary="List tenant supplier registry")
def list_suppliers(
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> list[SupplierResponse]:
    return SupplierService(db).list_suppliers(tenant.organization_id)
