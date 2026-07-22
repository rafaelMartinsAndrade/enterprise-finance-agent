from app.models.organization import Organization
from app.repositories.base import Repository


class OrganizationRepository(Repository):
    def create(self, *, name: str, slug: str) -> Organization:
        record = Organization(name=name, slug=slug)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.session.query(Organization).filter(Organization.slug == slug).one_or_none()

    def list_all(self) -> list[Organization]:
        return list(self.session.query(Organization).order_by(Organization.name.asc()).all())
