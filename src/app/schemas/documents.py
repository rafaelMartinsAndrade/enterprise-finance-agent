from pydantic import Field

from app.schemas.common import AppBaseModel, DocumentStatus, SourceType


class DocumentVersionResponse(AppBaseModel):
    id: int
    version_number: int
    filename: str
    content_type: str
    processing_status: DocumentStatus
    page_count: int
    character_count: int
    is_active: bool
    error_message: str | None


class DocumentListItem(AppBaseModel):
    id: int
    title: str
    status: DocumentStatus
    source_type: SourceType
    current_version_number: int | None
    latest_run_id: int | None
    tags: list[str]


class DocumentDetailResponse(DocumentListItem):
    latest_error_message: str | None
    versions: list[DocumentVersionResponse]


class DocumentUploadResponse(AppBaseModel):
    document_id: int = Field(ge=1)
    version_id: int = Field(ge=1)
    run_id: int = Field(ge=1)
    status: DocumentStatus


class DocumentActionResponse(AppBaseModel):
    document_id: int = Field(ge=1)
    status: DocumentStatus
    detail: str
