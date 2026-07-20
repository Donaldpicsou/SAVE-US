"""Private local media storage for the hackathon demonstration."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class PhotoUploadError(ValueError):
    """Raised when an uploaded missing-person image is unsafe or unsupported."""


IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    b"\x89PNG\r\n\x1a\n": ("png", "image/png"),
    b"GIF87a": ("gif", "image/gif"),
    b"GIF89a": ("gif", "image/gif"),
}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}


def image_metadata(upload: FileStorage, *, max_bytes: int) -> tuple[str, int]:
    """Validate filename, size, declared type, and binary signature of an image."""
    filename = secure_filename(upload.filename or "")
    if not filename or "." not in filename:
        raise PhotoUploadError("Choose a PNG, JPG, or GIF image.")
    extension = filename.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise PhotoUploadError("Only PNG, JPG, and GIF images are allowed.")

    upload.stream.seek(0, 2)
    file_size = upload.stream.tell()
    upload.stream.seek(0)
    if file_size == 0:
        raise PhotoUploadError("The selected image is empty.")
    if file_size > max_bytes:
        raise PhotoUploadError("The image must be 5 MB or smaller.")

    signature = upload.stream.read(16)
    upload.stream.seek(0)
    detected = next(
        (metadata for prefix, metadata in IMAGE_SIGNATURES.items() if signature.startswith(prefix)),
        None,
    )
    if detected is None:
        raise PhotoUploadError("The selected file is not a supported image.")

    detected_extension, detected_mimetype = detected
    extension_matches = extension == detected_extension or (
        extension == "jpeg" and detected_extension == "jpg"
    )
    if not extension_matches:
        raise PhotoUploadError("The file extension does not match the image content.")
    if upload.mimetype and upload.mimetype not in {detected_mimetype, "application/octet-stream"}:
        raise PhotoUploadError("The declared file type does not match the image content.")
    return detected_extension, file_size


def store_missing_person_photo(
    upload: FileStorage,
    *,
    upload_root: str | Path,
    alert_id: str,
    max_bytes: int,
) -> str:
    """Store a missing-person image through the shared private alert-media helper."""
    return store_alert_photo(
        upload,
        upload_root=upload_root,
        alert_id=alert_id,
        category="missing_person",
        max_bytes=max_bytes,
    )


def store_alert_photo(
    upload: FileStorage,
    *,
    upload_root: str | Path,
    alert_id: str,
    category: str,
    max_bytes: int,
) -> str:
    """Store one validated category-specific image outside ``static``."""
    extension, _ = image_metadata(upload, max_bytes=max_bytes)
    relative_path = Path(category) / alert_id / f"{uuid4().hex}.{extension}"
    target = Path(upload_root) / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    upload.save(target)
    return relative_path.as_posix()


def private_media_path(upload_root: str | Path, relative_path: str) -> Path | None:
    """Resolve a stored relative path only when it stays inside the private upload root."""
    root = Path(upload_root).resolve()
    candidate = (root / relative_path).resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def delete_private_media(upload_root: str | Path, relative_path: str | None) -> None:
    """Remove a replaced private file, ignoring an already absent demo file."""
    if not relative_path:
        return
    path = private_media_path(upload_root, relative_path)
    if path is not None:
        path.unlink(missing_ok=True)
