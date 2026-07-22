from pydantic import Field

from app.schemas.common import AppBaseModel


class ErrorInfo(AppBaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(AppBaseModel):
    request_id: str
    error: ErrorInfo
