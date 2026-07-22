from app.core.exceptions import AuthenticationError
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import DemoLoginRequest, DemoLoginResponse, TenantContext


class AuthService:
    def __init__(self, session) -> None:
        self.organization_repository = OrganizationRepository(session)
        self.user_repository = UserRepository(session)

    def demo_login(self, payload: DemoLoginRequest) -> DemoLoginResponse:
        organization = self.organization_repository.get_by_slug(payload.organization_slug)
        if organization is None:
            raise AuthenticationError("Unknown organization slug.")
        user = self.user_repository.get_by_org_and_email(
            organization_id=organization.id,
            email=payload.user_email,
        )
        if user is None:
            raise AuthenticationError("Unknown user for organization.")

        tenant = TenantContext(
            organization_id=organization.id,
            organization_slug=organization.slug,
            user_id=user.id,
            user_email=user.email,
            user_name=user.full_name,
            user_role=user.role,
        )
        return DemoLoginResponse(
            tenant=tenant,
            required_headers={
                "X-Organization-Slug": organization.slug,
                "X-User-Email": user.email,
            },
        )
