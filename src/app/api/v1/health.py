from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health_service import HealthService


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    service = HealthService()
    return service.get_health()
