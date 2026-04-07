from .models import Document
from vector_store import delete_file_from_vector_store, upload_file_to_vector_store


def sync_document_to_vector_store(document: Document) -> str:
    return upload_file_to_vector_store(
        local_path=document.file.path,
        original_name=document.file.name,
        username=document.school.username,
    )


def remove_document_from_vector_store(document: Document) -> None:
    if not document.vector_store_file_id:
        return

    delete_file_from_vector_store(document.vector_store_file_id)
