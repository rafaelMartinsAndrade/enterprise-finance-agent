from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.organizations import OrganizationResponse, UserResponse


class OrganizationService:
    def __init__(self, session) -> None:
        self.organization_repository = OrganizationRepository(session)
        self.user_repository = UserRepository(session)

    def list_organizations(self) -> list[OrganizationResponse]:
        return [
            OrganizationResponse(id=item.id, name=item.name, slug=item.slug)
            for item in self.organization_repository.list_all()
        ]

    def list_users(self, organization_slug: str) -> list[UserResponse]:
        organization = self.organization_repository.get_by_slug(organization_slug)
        if organization is None:
            return []
        return [
            UserResponse(
                id=item.id,
                email=item.email,
                full_name=item.full_name,
                role=item.role,
            )
            for item in self.user_repository.list_by_organization(organization.id)
        ]
