from sqlalchemy import delete

from app.models.draft_pre_entry import DraftPreEntry
from app.models.finance_document import FinanceDocument
from app.models.finance_document_version import FinanceDocumentVersion
from app.repositories.base import Repository


class FinanceRepository(Repository):
    def create_document(
        self,
        *,
        organization_id: int,
        created_by_user_id: int,
        title: str,
        source_type: str,
        tags: list[str],
        status: str = "uploaded",
    ) -> FinanceDocument:
        record = FinanceDocument(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            title=title,
            source_type=source_type,
            tags_json=tags,
            status=status,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def create_version(
        self,
        *,
        organization_id: int,
        document_id: int,
        created_by_user_id: int,
        version_number: int,
        filename: str,
        content_type: str,
        storage_path: str,
        checksum: str,
        processing_status: str = "uploaded",
    ) -> FinanceDocumentVersion:
        record = FinanceDocumentVersion(
            organization_id=organization_id,
            document_id=document_id,
            created_by_user_id=created_by_user_id,
            version_number=version_number,
            filename=filename,
            content_type=content_type,
            storage_path=storage_path,
            checksum=checksum,
            processing_status=processing_status,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_document(self, document_id: int) -> FinanceDocument | None:
        return self.session.get(FinanceDocument, document_id)

    def get_version(self, version_id: int) -> FinanceDocumentVersion | None:
        return self.session.get(FinanceDocumentVersion, version_id)

    def list_documents(self, organization_id: int) -> list[FinanceDocument]:
        return (
            self.session.query(FinanceDocument)
            .filter(FinanceDocument.organization_id == organization_id)
            .order_by(FinanceDocument.updated_at.desc())
            .all()
        )

    def list_versions(self, document_id: int) -> list[FinanceDocumentVersion]:
        return (
            self.session.query(FinanceDocumentVersion)
            .filter(FinanceDocumentVersion.document_id == document_id)
            .order_by(FinanceDocumentVersion.version_number.desc())
            .all()
        )

    def get_latest_version(self, document_id: int) -> FinanceDocumentVersion | None:
        return (
            self.session.query(FinanceDocumentVersion)
            .filter(FinanceDocumentVersion.document_id == document_id)
            .order_by(FinanceDocumentVersion.version_number.desc())
            .first()
        )

    def update_document(
        self,
        document: FinanceDocument,
        *,
        status: str | None = None,
        latest_run_id: int | None = None,
        latest_error_message: str | None = None,
        current_version_number: int | None = None,
    ) -> FinanceDocument:
        if status is not None:
            document.status = status
        if latest_run_id is not None:
            document.latest_run_id = latest_run_id
        document.latest_error_message = latest_error_message
        if current_version_number is not None:
            document.current_version_number = current_version_number
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def update_version(
        self,
        version: FinanceDocumentVersion,
        *,
        processing_status: str,
        page_count: int | None = None,
        character_count: int | None = None,
        error_message: str | None = None,
        extraction_metadata_json: dict | None = None,
        is_active: bool | None = None,
    ) -> FinanceDocumentVersion:
        version.processing_status = processing_status
        if page_count is not None:
            version.page_count = page_count
        if character_count is not None:
            version.character_count = character_count
        version.error_message = error_message
        if extraction_metadata_json is not None:
            version.extraction_metadata_json = extraction_metadata_json
        if is_active is not None:
            version.is_active = is_active
        self.session.add(version)
        self.session.commit()
        self.session.refresh(version)
        return version

    def deactivate_other_versions(self, document_id: int, active_version_id: int) -> None:
        versions = (
            self.session.query(FinanceDocumentVersion)
            .filter(FinanceDocumentVersion.document_id == document_id)
            .all()
        )
        for version in versions:
            version.is_active = version.id == active_version_id
            self.session.add(version)
        self.session.commit()

    def create_or_update_draft(
        self,
        *,
        organization_id: int,
        agent_run_id: int,
        supplier_id: int | None,
        supplier_name: str,
        document_number: str,
        issue_date: str | None,
        due_date: str | None,
        amount: float,
        currency: str,
        category: str,
        description: str,
        status: str,
        payload_json: dict,
    ) -> DraftPreEntry:
        existing = self.get_draft_by_run(agent_run_id)
        if existing is None:
            existing = DraftPreEntry(
                organization_id=organization_id,
                agent_run_id=agent_run_id,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                document_number=document_number,
                issue_date=issue_date,
                due_date=due_date,
                amount=amount,
                currency=currency,
                category=category,
                description=description,
                status=status,
                payload_json=payload_json,
            )
        else:
            existing.supplier_id = supplier_id
            existing.supplier_name = supplier_name
            existing.document_number = document_number
            existing.issue_date = issue_date
            existing.due_date = due_date
            existing.amount = amount
            existing.currency = currency
            existing.category = category
            existing.description = description
            existing.status = status
            existing.payload_json = payload_json
        self.session.add(existing)
        self.session.commit()
        self.session.refresh(existing)
        return existing

    def get_draft_by_run(self, agent_run_id: int) -> DraftPreEntry | None:
        return (
            self.session.query(DraftPreEntry)
            .filter(DraftPreEntry.agent_run_id == agent_run_id)
            .one_or_none()
        )

    def find_duplicate_drafts(
        self,
        *,
        organization_id: int,
        supplier_name: str | None,
        document_number: str | None,
        amount: float | None,
    ) -> list[DraftPreEntry]:
        query = self.session.query(DraftPreEntry).filter(DraftPreEntry.organization_id == organization_id)
        if supplier_name:
            query = query.filter(DraftPreEntry.supplier_name.ilike(f"%{supplier_name}%"))
        if document_number:
            query = query.filter(DraftPreEntry.document_number == document_number)
        if amount is not None:
            query = query.filter(DraftPreEntry.amount == amount)
        return query.order_by(DraftPreEntry.created_at.desc()).all()

    def delete_document(self, document: FinanceDocument) -> None:
        versions = self.list_versions(document.id)
        for version in versions:
            self.session.execute(delete(FinanceDocumentVersion).where(FinanceDocumentVersion.id == version.id))
        self.session.delete(document)
        self.session.commit()
