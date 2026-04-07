import mimetypes
import os
import shutil
from contextlib import suppress
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI


load_dotenv()

DEFAULT_BASE_URL = "https://ai.api.cloud.yandex.net/v1"
BASE_DIR = Path(__file__).resolve().parent
LOCAL_DATASET_ROOT = BASE_DIR / "local_dataset"
LOCAL_DATASET_PREFIX = "local:"


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} пустой (env var {name} не задан)")
    return value


def get_bot_token() -> str:
    value = _get_required_env("BOT_TOKEN")
    if value in _PLACEHOLDER_VALUES:
        raise RuntimeError(f"BOT_TOKEN не настроен (установлен placeholder)")
    return value


def get_vector_store_id() -> str:
    return _get_required_env("VECTOR_STORE_ID")


def get_folder_id() -> str:
    return _get_required_env("YANDEX_FOLDER_ID")


def _get_client_kwargs() -> dict[str, str]:
    return {
        "api_key": _get_required_env("YANDEX_API_KEY"),
        "base_url": os.getenv("YANDEX_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        "project": get_folder_id(),
    }


_PLACEHOLDER_VALUES = {
    "replace-with-yandex-api-key",
    "replace-with-yandex-folder-id",
    "replace-with-vector-store-id",
    "replace-with-telegram-bot-token",
}


def _is_real_value(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and stripped not in _PLACEHOLDER_VALUES


def has_remote_vector_store_config() -> bool:
    return all(
        _is_real_value(os.getenv(name, ""))
        for name in ("YANDEX_API_KEY", "YANDEX_FOLDER_ID", "VECTOR_STORE_ID")
    )


def get_sync_client() -> OpenAI:
    return OpenAI(**_get_client_kwargs())


def get_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(**_get_client_kwargs())


def build_remote_filename(username: str, original_name: str) -> str:
    safe_name = Path(original_name).name
    return f"{username}__{safe_name}"


def _ensure_local_dataset_dir(username: str) -> Path:
    user_dir = LOCAL_DATASET_ROOT / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _build_local_dataset_id(username: str, dataset_name: str) -> str:
    return f"{LOCAL_DATASET_PREFIX}{username}/{dataset_name}"


def is_local_dataset_id(file_id: str) -> bool:
    return file_id.startswith(LOCAL_DATASET_PREFIX)


def _local_dataset_path(file_id: str) -> Path:
    relative_path = file_id.removeprefix(LOCAL_DATASET_PREFIX)
    return LOCAL_DATASET_ROOT / relative_path


def list_local_dataset_files() -> list[Path]:
    if not LOCAL_DATASET_ROOT.exists():
        return []
    return sorted(path for path in LOCAL_DATASET_ROOT.rglob("*") if path.is_file())


def upload_file_to_vector_store(*, local_path: str, original_name: str, username: str) -> str:
    remote_filename = build_remote_filename(username, original_name)

    if not has_remote_vector_store_config():
        target_dir = _ensure_local_dataset_dir(username)
        target_path = target_dir / remote_filename
        shutil.copy2(local_path, target_path)
        return _build_local_dataset_id(username, remote_filename)

    mime_type = mimetypes.guess_type(remote_filename)[0] or "application/octet-stream"
    client = get_sync_client()

    vector_store_file = client.vector_stores.files.upload_and_poll(
        vector_store_id=get_vector_store_id(),
        file=(remote_filename, Path(local_path), mime_type),
        attributes={
            "username": username,
            "original_filename": Path(original_name).name,
        },
        poll_interval_ms=1000,
    )
    return vector_store_file.id


def delete_file_from_vector_store(file_id: str) -> None:
    if is_local_dataset_id(file_id):
        local_path = _local_dataset_path(file_id)
        if local_path.exists():
            local_path.unlink()
            with suppress(OSError):
                local_path.parent.rmdir()
        return

    client = get_sync_client()
    client.vector_stores.files.delete(
        file_id=file_id,
        vector_store_id=get_vector_store_id(),
    )
