from app.core.config import settings
from app.core.exceptions import DomainValidationError, NotFoundError
from app.repositories.finance_repository import FinanceRepository
from app.schemas.auth import TenantContext
from app.schemas.common import DocumentStatus, SourceType
from app.schemas.documents import DocumentDetailResponse, DocumentListItem, DocumentUploadResponse, DocumentVersionResponse
from app.services.storage_service import StorageService
from app.services.workflow_service import WorkflowService


class DocumentService:
    def __init__(self, session) -> None:
        self.session = session
        self.finance_repository = FinanceRepository(session)
        self.storage_service = StorageService()
        self.workflow_service = WorkflowService(session)

    async def upload_document(
        self,
        *,
        tenant: TenantContext,
        title: str,
        tags: list[str],
        upload,
        idempotency_key: str | None,
    ) -> DocumentUploadResponse:
        self._validate_upload(upload)
        if idempotency_key:
            existing = self.workflow_service.get_existing_run_by_idempotency_key(
                tenant=tenant,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                return DocumentUploadResponse(
                    document_id=existing.document_id,
                    version_id=existing.version_id,
                    run_id=existing.id,
                    status=DocumentStatus(existing.status),
                )
        document = self.finance_repository.create_document(
            organization_id=tenant.organization_id,
            created_by_user_id=tenant.user_id,
            title=title,
            source_type=SourceType.upload.value,
            tags=tags,
        )
        storage_path, checksum, _ = await self.storage_service.save_upload(
            organization_slug=tenant.organization_slug,
            document_id=document.id,
            version_number=1,
            upload=upload,
        )
        version = self.finance_repository.create_version(
            organization_id=tenant.organization_id,
            document_id=document.id,
            created_by_user_id=tenant.user_id,
            version_number=1,
            filename=upload.filename or f"document-{document.id}",
            content_type=upload.content_type or "application/octet-stream",
            storage_path=storage_path,
            checksum=checksum,
        )
        started = self.workflow_service.start_run(
            tenant=tenant,
            document_id=document.id,
            version_id=version.id,
            idempotency_key=idempotency_key,
        )
        return DocumentUploadResponse(
            document_id=document.id,
            version_id=version.id,
            run_id=started.run.id,
            status=DocumentStatus(started.run.status),
        )

    async def update_document(
        self,
        *,
        tenant: TenantContext,
        document_id: int,
        title: str | None,
        tags: list[str] | None,
        upload,
        idempotency_key: str | None,
    ) -> DocumentUploadResponse:
        self._validate_upload(upload)
        if idempotency_key:
            existing = self.workflow_service.get_existing_run_by_idempotency_key(
                tenant=tenant,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                if existing.document_id != document_id:
                    raise DomainValidationError("Idempotency key already belongs to another document.")
                return DocumentUploadResponse(
                    document_id=existing.document_id,
                    version_id=existing.version_id,
                    run_id=existing.id,
                    status=DocumentStatus(existing.status),
                )
        document = self._get_tenant_document(tenant=tenant, document_id=document_id)
        latest_version = self.finance_repository.get_latest_version(document.id)
        next_version_number = 1 if latest_version is None else latest_version.version_number + 1
        if title:
            document.title = title
        if tags is not None:
            document.tags_json = tags
        self.session.add(document)
        self.session.commit()

        storage_path, checksum, _ = await self.storage_service.save_upload(
            organization_slug=tenant.organization_slug,
            document_id=document.id,
            version_number=next_version_number,
            upload=upload,
        )
        if latest_version is not None and latest_version.checksum == checksum:
            raise DomainValidationError("New document version is identical to latest version.")
        version = self.finance_repository.create_version(
            organization_id=tenant.organization_id,
            document_id=document.id,
            created_by_user_id=tenant.user_id,
            version_number=next_version_number,
            filename=upload.filename or f"document-{document.id}",
            content_type=upload.content_type or "application/octet-stream",
            storage_path=storage_path,
            checksum=checksum,
        )
        started = self.workflow_service.start_run(
            tenant=tenant,
            document_id=document.id,
            version_id=version.id,
            idempotency_key=idempotency_key,
        )
        return DocumentUploadResponse(
            document_id=document.id,
            version_id=version.id,
            run_id=started.run.id,
            status=DocumentStatus(started.run.status),
        )

    def list_documents(self, *, tenant: TenantContext) -> list[DocumentListItem]:
        return [
            DocumentListItem(
                id=item.id,
                title=item.title,
                status=DocumentStatus(item.status),
                source_type=SourceType(item.source_type),
                current_version_number=item.current_version_number,
                latest_run_id=item.latest_run_id,
                tags=item.tags_json,
            )
            for item in self.finance_repository.list_documents(tenant.organization_id)
        ]

    def get_document(self, *, tenant: TenantContext, document_id: int) -> DocumentDetailResponse:
        document = self._get_tenant_document(tenant=tenant, document_id=document_id)
        versions = self.finance_repository.list_versions(document.id)
        return DocumentDetailResponse(
            id=document.id,
            title=document.title,
            status=DocumentStatus(document.status),
            source_type=SourceType(document.source_type),
            current_version_number=document.current_version_number,
            latest_run_id=document.latest_run_id,
            latest_error_message=document.latest_error_message,
            tags=document.tags_json,
            versions=[
                DocumentVersionResponse(
                    id=version.id,
                    version_number=version.version_number,
                    filename=version.filename,
                    content_type=version.content_type,
                    processing_status=DocumentStatus(version.processing_status),
                    page_count=version.page_count,
                    character_count=version.character_count,
                    is_active=version.is_active,
                    error_message=version.error_message,
                )
                for version in versions
            ],
        )

    def _get_tenant_document(self, *, tenant: TenantContext, document_id: int):
        document = self.finance_repository.get_document(document_id)
        if document is None or document.organization_id != tenant.organization_id:
            raise NotFoundError("Document not found for tenant.")
        return document

    def _validate_upload(self, upload) -> None:
        if upload.content_type not in settings.allowed_upload_types:
            raise DomainValidationError("Unsupported file type for finance workflow ingestion.")
