from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_api_token
from app.core.db import get_db
from app.schemas.organizations import OrganizationResponse, UserResponse
from app.services.organization_service import OrganizationService


router = APIRouter()


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List demo organizations",
)
def list_organizations(
    _: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> list[OrganizationResponse]:
    return OrganizationService(db).list_organizations()


@router.get(
    "/{organization_slug}/users",
    response_model=list[UserResponse],
    summary="List users for one organization",
)
def list_users(
    organization_slug: str,
    _: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    return OrganizationService(db).list_users(organization_slug)
