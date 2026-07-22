from pydantic import Field

from app.schemas.common import AppBaseModel


class TenantContext(AppBaseModel):
    organization_id: int = Field(ge=1)
    organization_slug: str
    user_id: int = Field(ge=1)
    user_email: str
    user_name: str
    user_role: str


class DemoLoginRequest(AppBaseModel):
    organization_slug: str = Field(min_length=3, max_length=80)
    user_email: str = Field(min_length=5, max_length=160)


class DemoLoginResponse(AppBaseModel):
    access_mode: str = "header-context"
    api_token_hint: str = "Use Authorization: Bearer change-me or your configured token."
    tenant: TenantContext
    required_headers: dict[str, str]
