from app.schemas.common import AppBaseModel


class OrganizationResponse(AppBaseModel):
    id: int
    name: str
    slug: str


class UserResponse(AppBaseModel):
    id: int
    email: str
    full_name: str
    role: str
