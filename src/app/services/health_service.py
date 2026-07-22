from pathlib import Path

from app.core.config import settings
from app.repositories.health_repository import HealthRepository
from app.schemas.health import HealthResponse


class HealthService:
    def __init__(self) -> None:
        self.health_repository = HealthRepository()

    def get_health(self) -> HealthResponse:
        persistence_ok = self.health_repository.check_persistence()
        storage_ok = Path(settings.storage_root).exists()
        checkpoint_ok = Path(settings.agent_checkpoint_path).parent.exists()
        return HealthResponse(
            status="ok" if persistence_ok and storage_ok and checkpoint_ok else "degraded",
            app="enterprise-finance-agent",
            persistence="reachable" if persistence_ok else "unreachable",
            storage="ready" if storage_ok else "missing",
            checkpointing="ready" if checkpoint_ok else "missing",
        )
