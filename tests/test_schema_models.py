from app.core.config import Settings
from app.schemas.agent import ApprovalDecisionRequest
from app.schemas.auth import DemoLoginRequest


def test_settings_and_schema_validation() -> None:
    settings = Settings(
        allowed_upload_types="text/plain, application/pdf",
        api_token="change-me-token",
    )

    assert settings.allowed_upload_types == ["text/plain", "application/pdf"]
    assert DemoLoginRequest(organization_slug="acme-finance", user_email="ana@acme.test").organization_slug == "acme-finance"

    try:
        ApprovalDecisionRequest(action="edit")
    except ValueError as exc:
        assert "edited_fields is required" in str(exc)
    else:
        raise AssertionError("edit approval should require edited_fields")
