import hashlib
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.root = Path(settings.storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_upload(
        self,
        *,
        organization_slug: str,
        document_id: int,
        version_number: int,
        upload: UploadFile,
    ) -> tuple[str, str, int]:
        content = await upload.read()
        checksum = hashlib.sha256(content).hexdigest()
        directory = self.root / organization_slug / f"document_{document_id}" / f"v{version_number}"
        directory.mkdir(parents=True, exist_ok=True)
        filename = upload.filename or f"document-{document_id}.bin"
        path = directory / filename
        path.write_bytes(content)
        return str(path), checksum, len(content)

    def delete_document_tree(self, *, organization_slug: str, document_id: int) -> None:
        directory = self.root / organization_slug / f"document_{document_id}"
        if not directory.exists():
            return
        for item in sorted(directory.rglob("*"), reverse=True):
            if item.is_file():
                item.unlink(missing_ok=True)
            elif item.is_dir():
                item.rmdir()
        directory.rmdir()
