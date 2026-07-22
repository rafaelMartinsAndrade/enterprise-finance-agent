from app.models.app_user import AppUser
from app.repositories.base import Repository


class UserRepository(Repository):
    def create(
        self,
        *,
        organization_id: int,
        email: str,
        full_name: str,
        role: str = "analyst",
    ) -> AppUser:
        record = AppUser(
            organization_id=organization_id,
            email=email.lower(),
            full_name=full_name,
            role=role,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_org_and_email(self, *, organization_id: int, email: str) -> AppUser | None:
        return (
            self.session.query(AppUser)
            .filter(
                AppUser.organization_id == organization_id,
                AppUser.email == email.lower(),
            )
            .one_or_none()
        )

    def list_by_organization(self, organization_id: int) -> list[AppUser]:
        return (
            self.session.query(AppUser)
            .filter(AppUser.organization_id == organization_id)
            .order_by(AppUser.full_name.asc())
            .all()
        )
