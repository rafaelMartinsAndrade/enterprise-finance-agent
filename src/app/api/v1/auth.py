from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.auth import DemoLoginRequest, DemoLoginResponse
from app.services.auth_service import AuthService


router = APIRouter()


@router.post(
    "/demo-login",
    response_model=DemoLoginResponse,
    summary="Validate organization and user for demo session headers",
)
def demo_login(payload: DemoLoginRequest, db: Session = Depends(get_db)) -> DemoLoginResponse:
    return AuthService(db).demo_login(payload)
