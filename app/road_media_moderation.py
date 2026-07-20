"""Private safety checks for optional road-accident photographs (T32)."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .media import IMAGE_SIGNATURES, private_media_path
from .models import Alert, AlertType


MEDIA_STATUS_CLEAR = "clear"
MEDIA_STATUS_NEEDS_MODERATION = "needs_moderation"
MEDIA_STATUS_BLOCKED = "blocked"
SERVER_MEDIA_SOURCE = "server_media_check"
OPENAI_MEDIA_SOURCE = "openai_responses_api"
FALLBACK_MEDIA_SOURCE = "conservative_demo_fallback"

MEDIA_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "reason"],
    "properties": {
        "status": {"type": "string", "enum": [MEDIA_STATUS_CLEAR, MEDIA_STATUS_NEEDS_MODERATION, MEDIA_STATUS_BLOCKED]},
        "reason": {"type": "string", "minLength": 1, "maxLength": 500},
    },
}

MEDIA_SYSTEM_INSTRUCTIONS = """You are the SAVE-US road-accident media safety reviewer.
Review the attached image only for whether it can be safely used in a community emergency alert.
Return only the requested JSON. Use status 'blocked' for graphic injury/death imagery, sexual content,
or content unsafe to share. Use 'needs_moderation' when the image is unclear, sensitive, or cannot be
assessed reliably. Use 'clear' only when it is non-graphic, relevant enough, and safe to share.
Write one concise, user-facing reason in English. Do not identify people or infer facts from the image."""


@dataclass(frozen=True)
class MediaModerationResult:
    """A private, auditable media decision used to update the alert lifecycle."""

    media_reference: str | None
    status: str
    reason: str
    source: str


def review_road_accident_media(
    alert: Alert,
    *,
    upload_root: str | Path,
    max_bytes: int,
    api_key: str | None,
    model: str,
    timeout: float,
    client_factory: Callable[..., Any] | None = None,
) -> MediaModerationResult:
    """Run server checks, then a visual review; fail safely to human moderation."""
    if alert.alert_type != AlertType.ROAD_ACCIDENT:
        raise ValueError("Road media moderation only accepts road-accident alerts.")
    details = alert.road_accident_details
    reference = details.media_references[0] if details and details.media_references else None
    if not reference:
        return MediaModerationResult(None, MEDIA_STATUS_CLEAR, "No photo was attached to this report.", SERVER_MEDIA_SOURCE)

    image = _load_valid_stored_image(upload_root, reference, max_bytes)
    if image is None:
        return MediaModerationResult(
            reference, MEDIA_STATUS_BLOCKED,
            "The uploaded photo could not pass the server safety checks and was not accepted for review.",
            SERVER_MEDIA_SOURCE,
        )
    if not api_key:
        return MediaModerationResult(
            reference, MEDIA_STATUS_NEEDS_MODERATION,
            "The photo needs a human safety check before this report can be shared.",
            FALLBACK_MEDIA_SOURCE,
        )

    extension, image_bytes, mime_type = image
    try:
        client = _make_client(api_key, timeout, client_factory)
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": MEDIA_SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": [
                    {"type": "input_text", "text": "Review this optional road-accident photo for safe community distribution."},
                    {"type": "input_image", "image_url": data_url},
                ]},
            ],
            text={"format": {"type": "json_schema", "name": "save_us_road_media_safety", "strict": True, "schema": MEDIA_OUTPUT_SCHEMA}},
            store=False,
        )
        raw_output = getattr(response, "output_text", None)
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise ValueError("The OpenAI response did not contain structured output text.")
        output = validate_media_output(json.loads(raw_output))
        return MediaModerationResult(reference, output["status"], output["reason"], OPENAI_MEDIA_SOURCE)
    except Exception:
        return MediaModerationResult(
            reference, MEDIA_STATUS_NEEDS_MODERATION,
            "The photo needs a human safety check before this report can be shared.",
            FALLBACK_MEDIA_SOURCE,
        )


def validate_media_output(payload: Mapping[str, Any]) -> dict[str, str]:
    """Accept only the small structured result needed by the report workflow."""
    if not isinstance(payload, Mapping) or set(payload) != {"status", "reason"}:
        raise ValueError("Media review output must contain only status and reason.")
    status = payload["status"]
    reason = payload["reason"]
    if status not in {MEDIA_STATUS_CLEAR, MEDIA_STATUS_NEEDS_MODERATION, MEDIA_STATUS_BLOCKED}:
        raise ValueError("Media review status is not supported.")
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 500:
        raise ValueError("Media review reason must be a concise non-empty string.")
    return {"status": status, "reason": reason.strip()}


def _load_valid_stored_image(upload_root: str | Path, reference: str, max_bytes: int) -> tuple[str, bytes, str] | None:
    """Repeat essential server checks before any file is sent to an external reviewer."""
    path = private_media_path(upload_root, reference)
    if path is None or path.stat().st_size == 0 or path.stat().st_size > max_bytes:
        return None
    image_bytes = path.read_bytes()
    detected = next((metadata for prefix, metadata in IMAGE_SIGNATURES.items() if image_bytes.startswith(prefix)), None)
    if detected is None:
        return None
    extension, mime_type = detected
    if Path(reference).suffix.lower().lstrip(".") not in {extension, "jpeg" if extension == "jpg" else extension}:
        return None
    return extension, image_bytes, mime_type


def _make_client(api_key: str, timeout: float, client_factory: Callable[..., Any] | None) -> Any:
    if client_factory is not None:
        return client_factory(api_key=api_key, timeout=timeout)
    from openai import OpenAI
    return OpenAI(api_key=api_key, timeout=timeout)


__all__ = [
    "FALLBACK_MEDIA_SOURCE",
    "MEDIA_STATUS_BLOCKED",
    "MEDIA_STATUS_CLEAR",
    "MEDIA_STATUS_NEEDS_MODERATION",
    "MediaModerationResult",
    "OPENAI_MEDIA_SOURCE",
    "SERVER_MEDIA_SOURCE",
    "review_road_accident_media",
    "validate_media_output",
]
