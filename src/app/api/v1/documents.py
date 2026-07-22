from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_tenant_context
from app.core.db import get_db
from app.schemas.auth import TenantContext
from app.schemas.documents import DocumentDetailResponse, DocumentListItem, DocumentUploadResponse
from app.services.document_service import DocumentService


router = APIRouter()


@router.get(
    "",
    response_model=list[DocumentListItem],
    summary="List organization documents",
)
def list_documents(
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> list[DocumentListItem]:
    return DocumentService(db).list_documents(tenant=tenant)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details and version history",
)
def get_document(
    document_id: int,
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    return DocumentService(db).get_document(tenant=tenant, document_id=document_id)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload finance document and start agent workflow",
)
async def upload_document(
    title: Annotated[str, Form(min_length=3, max_length=200)],
    tags: Annotated[str, Form()] = "",
    idempotency_key: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    normalized_tags = [item.strip() for item in tags.split(",") if item.strip()]
    return await DocumentService(db).upload_document(
        tenant=tenant,
        title=title,
        tags=normalized_tags,
        upload=file,
        idempotency_key=idempotency_key,
    )


@router.put(
    "/{document_id}",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a new version of an existing document",
)
async def update_document(
    document_id: int,
    file: UploadFile = File(...),
    title: Annotated[str | None, Form()] = None,
    tags: Annotated[str | None, Form()] = None,
    idempotency_key: Annotated[str | None, Form()] = None,
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    normalized_tags = None if tags is None else [item.strip() for item in tags.split(",") if item.strip()]
    return await DocumentService(db).update_document(
        tenant=tenant,
        document_id=document_id,
        title=title,
        tags=normalized_tags,
        upload=file,
        idempotency_key=idempotency_key,
    )
