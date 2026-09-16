import hashlib
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


def save_upload(file: BinaryIO, original_name: str) -> tuple[str, str, str]:
    """保存上传文件，返回 (file_id, sha256, saved_path)。"""
    content = file.read()
    sha256 = hashlib.sha256(content).hexdigest()
    file_id = str(uuid.uuid4())
    ext = Path(original_name).suffix or ".xlsx"
    filename = f"{file_id}{ext}"
    upload_path = Path(settings.upload_dir) / filename
    upload_path.write_bytes(content)
    return file_id, sha256, str(upload_path)


def get_upload_path(file_id: str, ext: str = ".xlsx") -> Path:
    return Path(settings.upload_dir) / f"{file_id}{ext}"


def ensure_result_dir() -> Path:
    result_dir = Path(settings.upload_dir) / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def save_result(content: bytes, suffix: str = ".xlsx") -> str:
    result_dir = ensure_result_dir()
    result_id = str(uuid.uuid4())
    result_path = result_dir / f"{result_id}{suffix}"
    result_path.write_bytes(content)
    return str(result_path)


def cleanup_upload(file_id: str, ext: str = ".xlsx"):
    path = get_upload_path(file_id, ext)
    if path.exists():
        path.unlink()


def cleanup_old_uploads(max_age_hours: int = 24):
    """清理超过指定小时的临时文件。"""
    import time

    now = time.time()
    for path in Path(settings.upload_dir).glob("*"):
        if path.is_file() and (now - path.stat().st_mtime) > max_age_hours * 3600:
            path.unlink()
