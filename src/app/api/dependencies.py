from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import AuthenticationError
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TenantContext


bearer_scheme = HTTPBearer(auto_error=False)


def require_api_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing bearer token.")
    if credentials.credentials != settings.api_token:
        raise AuthenticationError("Invalid API token.")
    return credentials.credentials


def require_tenant_context(
    _: Annotated[str, Depends(require_api_token)],
    db: Session = Depends(get_db),
    organization_slug: Annotated[str | None, Header(alias="X-Organization-Slug")] = None,
    user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> TenantContext:
    if not organization_slug or not user_email:
        raise AuthenticationError("Missing tenant headers.")

    organization = OrganizationRepository(db).get_by_slug(organization_slug)
    if organization is None:
        raise AuthenticationError("Unknown organization slug.")
    user = UserRepository(db).get_by_org_and_email(
        organization_id=organization.id,
        email=user_email,
    )
    if user is None:
        raise AuthenticationError("Unknown user for organization.")

    return TenantContext(
        organization_id=organization.id,
        organization_slug=organization.slug,
        user_id=user.id,
        user_email=user.email,
        user_name=user.full_name,
        user_role=user.role,
    )
