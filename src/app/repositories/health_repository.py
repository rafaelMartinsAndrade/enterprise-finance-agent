from sqlalchemy import text

from app.core.db import SessionLocal


class HealthRepository:
    def check_persistence(self) -> bool:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
