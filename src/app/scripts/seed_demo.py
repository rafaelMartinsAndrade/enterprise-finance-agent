from app import models  # noqa: F401
from app.core.db import SessionLocal, engine
from app.models.base import Base
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.user_repository import UserRepository


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        organizations = OrganizationRepository(session)
        users = UserRepository(session)
        suppliers = SupplierRepository(session)

        acme = organizations.get_by_slug("acme-finance")
        if acme is None:
            acme = organizations.create(name="ACME Finance", slug="acme-finance")
        northwind = organizations.get_by_slug("northwind-ops")
        if northwind is None:
            northwind = organizations.create(name="Northwind Ops", slug="northwind-ops")

        if users.get_by_org_and_email(organization_id=acme.id, email="ana@acme.demo") is None:
            users.create(
                organization_id=acme.id,
                email="ana@acme.demo",
                full_name="Ana Martins",
                role="finance-manager",
            )
        if users.get_by_org_and_email(organization_id=northwind.id, email="bruno@northwind.demo") is None:
            users.create(
                organization_id=northwind.id,
                email="bruno@northwind.demo",
                full_name="Bruno Andrade",
                role="ap-analyst",
            )

        existing_codes = {item.supplier_code for item in suppliers.list_by_organization(acme.id)}
        seed_rows = [
            (acme.id, "SUP-001", "AWS Brasil Cloud", "12.345.678/0001-01", "cloud", 15),
            (acme.id, "SUP-002", "Office Planet", "98.765.432/0001-10", "office", 30),
            (acme.id, "SUP-003", "Consulting Prime", "44.111.222/0001-55", "professional-services", 20),
            (northwind.id, "SUP-900", "Northwind Telecom", "20.111.000/0001-90", "telecom", 10),
        ]
        for org_id, code, name, tax_id, category, terms in seed_rows:
            if code in existing_codes and org_id == acme.id:
                continue
            org_existing = {item.supplier_code for item in suppliers.list_by_organization(org_id)}
            if code in org_existing:
                continue
            suppliers.create(
                organization_id=org_id,
                supplier_code=code,
                legal_name=name,
                tax_id=tax_id,
                default_category=category,
                payment_terms_days=terms,
            )
            print(f"seeded supplier {code}")


if __name__ == "__main__":
    main()
