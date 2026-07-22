from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core import db as core_db
from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def seeded_session(engine, tmp_path: Path) -> Generator[Session, None, None]:
    settings.storage_root = str(tmp_path / "storage")
    settings.agent_checkpoint_path = str(tmp_path / "checkpoints" / "agent-checkpoints.db")
    settings.api_token = "change-me"
    settings.document_analysis_provider = "mock"
    settings.category_provider = "mock"
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    core_db.SessionLocal = session_factory
    Path(settings.agent_checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    with Session(engine) as session:
        organization_repo = OrganizationRepository(session)
        user_repo = UserRepository(session)
        supplier_repo = SupplierRepository(session)
        acme = organization_repo.create(name="ACME Finance", slug="acme-finance")
        northwind = organization_repo.create(name="Northwind Ops", slug="northwind-ops")
        user_repo.create(
            organization_id=acme.id,
            email="ana@acme.test",
            full_name="Ana Finance",
            role="finance-manager",
        )
        user_repo.create(
            organization_id=northwind.id,
            email="bruno@northwind.test",
            full_name="Bruno Ops",
            role="ap-analyst",
        )
        supplier_repo.create(
            organization_id=acme.id,
            supplier_code="SUP-001",
            legal_name="AWS Brasil Cloud",
            tax_id="12.345.678/0001-01",
            default_category="cloud",
            payment_terms_days=15,
        )
        supplier_repo.create(
            organization_id=acme.id,
            supplier_code="SUP-002",
            legal_name="Office Planet",
            tax_id="98.765.432/0001-10",
            default_category="office",
            payment_terms_days=30,
        )
        supplier_repo.create(
            organization_id=acme.id,
            supplier_code="SUP-003",
            legal_name="Consulting Prime",
            tax_id="44.111.222/0001-55",
            default_category="professional-services",
            payment_terms_days=20,
        )
        supplier_repo.create(
            organization_id=northwind.id,
            supplier_code="SUP-900",
            legal_name="Northwind Telecom",
            tax_id="20.111.000/0001-90",
            default_category="telecom",
            payment_terms_days=10,
        )
        yield session


@pytest.fixture()
def client(engine, seeded_session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[core_db.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def acme_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer change-me",
        "X-Organization-Slug": "acme-finance",
        "X-User-Email": "ana@acme.test",
    }


@pytest.fixture()
def northwind_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer change-me",
        "X-Organization-Slug": "northwind-ops",
        "X-User-Email": "bruno@northwind.test",
    }
