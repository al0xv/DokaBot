import logging
from pathlib import Path

from .models import Document
from vector_store import (
    build_remote_filename,
    delete_file_from_vector_store,
    has_remote_vector_store_config,
    upload_file_to_vector_store,
)

logger = logging.getLogger(__name__)


def sync_document_to_vector_store(document: Document) -> None:
    upload_file_to_vector_store(
        local_path=document.file.path,
        original_name=Path(document.file.name).name,
        username=document.school.username,
    )


def _build_file_id_for_document(document: Document) -> str | None:
    """Reconstruct the file_id used for vector store operations."""
    if has_remote_vector_store_config():
        # Remote mode: we don't store the ID, so we can't reliably delete
        logger.warning(
            "Cannot delete document from remote vector store: "
            "vector_store_file_id is not stored. "
            "Consider re-adding the field to the model."
        )
        return None
    # Local mode: reconstruct the ID from the original filename
    original_name = Path(document.file.name).name
    remote_name = build_remote_filename(document.school.username, original_name)
    return f"local:{document.school.username}/{remote_name}"


def remove_document_from_vector_store(document: Document) -> None:
    file_id = _build_file_id_for_document(document)
    if file_id is None:
        return
    delete_file_from_vector_store(file_id)
