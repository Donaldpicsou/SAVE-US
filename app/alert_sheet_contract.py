"""Public-safe, versioned content contract for future SAVE-US alert sheets.

The contract is deliberately independent from HTML, PDF, sharing, or storage.
Those delivery mechanisms (T50–T53) must consume this single representation
instead of reading report-detail models directly.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .models import Alert, AlertStatus, AlertType
from .media import authorised_public_media_source


ALERT_SHEET_SCHEMA_VERSION = "save-us.alert-sheet.v2"
ALERT_SHEET_SOURCE = "Source: SAVE-US"

# Phone-like sequences, latitude/longitude pairs, and conventional numbered
# street-address patterns are never necessary for a public alert sheet.
PUBLIC_CONTACT_PATTERN = re.compile(r"(?:\+?\d[\s().-]*){7,}\d")
GPS_COORDINATE_PATTERN = re.compile(r"-?\d{1,2}\.\d{3,}\s*[,;/]\s*-?\d{1,3}\.\d{3,}")
PRECISE_ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+(?:[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.'-]*\s+){0,3}"
    r"(?:street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|rue|route|adresse|address)\b",
    re.IGNORECASE,
)

ALERT_SHEET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "alert_id",
        "title",
        "category",
        "category_label",
        "summary",
        "approximate_location",
        "coverage",
        "published_at",
        "published_label",
        "status",
        "safety_guidance",
        "expires_at",
        "expires_label",
        "public_media",
        "source",
    ],
    "properties": {
        "schema_version": {"enum": [ALERT_SHEET_SCHEMA_VERSION]},
        "alert_id": {"type": "string"},
        "title": {"type": "string", "minLength": 1, "maxLength": 180},
        "category": {"type": "string", "enum": [item.value for item in AlertType]},
        "category_label": {"type": "string"},
        "summary": {"type": "string", "minLength": 1, "maxLength": 1000},
        "approximate_location": {"type": "string"},
        "coverage": {"type": "string"},
        "published_at": {"type": "string", "format": "date-time"},
        "published_label": {"type": "string"},
        "status": {"enum": [AlertStatus.PUBLISHED.value]},
        "safety_guidance": {"type": "string"},
        "expires_at": {"type": ["string", "null"], "format": "date-time"},
        "expires_label": {"type": ["string", "null"]},
        "public_media": {
            "type": ["object", "null"],
            "properties": {
                "kind": {"const": "identification_photo"},
                "alt": {"type": "string", "maxLength": 240},
            },
        },
        "source": {"const": ALERT_SHEET_SOURCE},
    },
}


class AlertSheetSafetyError(ValueError):
    """Raised when an alert cannot safely be represented in an external sheet."""


def build_alert_sheet(alert: Alert, *, generated_at: datetime | None = None) -> dict[str, Any]:
    """Build the only allowed public payload for a printable or shareable sheet.

    This function never exports private contacts, manual accident locations,
    coordinates, internal reasons, audit records, or original media paths.
    An explicitly authorised missing-person or abduction identification photo
    is represented only by safe metadata; its derived URL is attached later.
    """
    if alert.status != AlertStatus.PUBLISHED:
        raise AlertSheetSafetyError("Only published alerts can have an alert sheet.")
    if not alert.title or not alert.title.strip():
        raise AlertSheetSafetyError("A published alert needs a public-safe title.")

    title = _validate_public_text(alert.title, "title", maximum=180)
    summary = _validate_public_text(
        alert.public_summary or "A SAVE-US alert has been published.",
        "public summary",
        maximum=1000,
    )
    published_at = _normalise_datetime(alert.published_at or alert.created_at)
    expires_at = _normalise_datetime(alert.expires_at) if alert.expires_at else None
    presentation = _presentation_for(alert)
    approximate_location = _safe_approximate_location(alert)
    # `generated_at` is accepted for deterministic tests and future PDF metadata,
    # but intentionally does not become a public incident field in version 1.
    _ = generated_at

    return {
        "schema_version": ALERT_SHEET_SCHEMA_VERSION,
        "alert_id": alert.id,
        "title": title,
        "category": alert.alert_type.value,
        "category_label": presentation["category_label"],
        "summary": summary,
        "approximate_location": approximate_location,
        "coverage": presentation["coverage"].format(country=alert.country, region=alert.region or alert.country),
        "published_at": published_at.isoformat(),
        "published_label": published_at.strftime("Published %d %b %Y · %H:%M UTC"),
        "status": AlertStatus.PUBLISHED.value,
        "safety_guidance": presentation["safety_guidance"],
        "expires_at": expires_at.isoformat() if expires_at else None,
        "expires_label": expires_at.strftime("Expires %d %b %Y · %H:%M UTC") if expires_at else None,
        "public_media": (
            {"kind": "identification_photo", "alt": f"Approved identification photo for {title}"}
            if authorised_public_media_source(alert)
            else None
        ),
        "source": ALERT_SHEET_SOURCE,
    }


def validate_alert_sheet(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a serialised sheet payload before an external delivery layer uses it."""
    if not isinstance(payload, Mapping):
        raise AlertSheetSafetyError("Alert-sheet payload must be an object.")
    expected_keys = set(ALERT_SHEET_SCHEMA["required"])
    if set(payload) != expected_keys:
        raise AlertSheetSafetyError("Alert-sheet payload has an invalid shape.")
    if payload["schema_version"] != ALERT_SHEET_SCHEMA_VERSION:
        raise AlertSheetSafetyError("Unsupported alert-sheet schema version.")
    if payload["source"] != ALERT_SHEET_SOURCE:
        raise AlertSheetSafetyError("Alert sheets must retain SAVE-US attribution.")
    if payload["category"] not in {item.value for item in AlertType}:
        raise AlertSheetSafetyError("Alert-sheet category is not supported.")
    if payload["status"] != AlertStatus.PUBLISHED.value:
        raise AlertSheetSafetyError("Only published alert sheets are valid.")
    for field, maximum in (("title", 180), ("summary", 1000), ("approximate_location", 300), ("coverage", 200), ("safety_guidance", 500)):
        value = payload[field]
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise AlertSheetSafetyError(f"Alert-sheet {field} is invalid.")
        _validate_public_text(value, field, maximum=maximum)
    if not isinstance(payload["alert_id"], str) or not payload["alert_id"].strip():
        raise AlertSheetSafetyError("Alert-sheet alert_id is invalid.")
    for field in ("category_label", "published_at", "published_label"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise AlertSheetSafetyError(f"Alert-sheet {field} is invalid.")
    for field in ("expires_at", "expires_label"):
        if payload[field] is not None and (not isinstance(payload[field], str) or not payload[field].strip()):
            raise AlertSheetSafetyError(f"Alert-sheet {field} is invalid.")
    public_media = payload["public_media"]
    if public_media is not None:
        if not isinstance(public_media, Mapping) or set(public_media) != {"kind", "alt"}:
            raise AlertSheetSafetyError("Alert-sheet public media is invalid.")
        if public_media["kind"] != "identification_photo":
            raise AlertSheetSafetyError("Alert-sheet public media kind is invalid.")
        if not isinstance(public_media["alt"], str):
            raise AlertSheetSafetyError("Alert-sheet public media alt text is invalid.")
        _validate_public_text(public_media["alt"], "public media alt text", maximum=240)
    return dict(payload)


def _presentation_for(alert: Alert) -> dict[str, str]:
    return {
        AlertType.MISSING_PERSON: {
            "category_label": "Missing person",
            "coverage": "Regional community search · {region}",
            "safety_guidance": "Share verified information only. Do not publish private family contact details or precise locations.",
        },
        AlertType.SUSPECTED_ABDUCTION: {
            "category_label": "Suspected abduction",
            "coverage": "Country-wide urgent alert · {country}",
            "safety_guidance": "Do not confront anyone involved. Share verified facts only and contact emergency services when there is immediate danger.",
        },
        AlertType.UNKNOWN_HOSPITAL_PATIENT: {
            "category_label": "Unknown hospital patient",
            "coverage": "Country-wide identification request · {country}",
            "safety_guidance": "Share only information needed for identification. Do not publish medical, family, or contact details.",
        },
        AlertType.ROAD_ACCIDENT: {
            "category_label": "Road accident",
            "coverage": "Regional road-safety alert · {region}",
            "safety_guidance": "Avoid the affected area and drive carefully. The location shown is approximate; exact coordinates and media remain protected.",
        },
    }[alert.alert_type]


def _safe_approximate_location(alert: Alert) -> str:
    """Use the public zone only when it does not look like precise location data."""
    fallback = " · ".join(part for part in (alert.region, alert.country) if part)
    zone = (alert.approximate_zone or "").strip()
    if not zone:
        return fallback or "CEMAC"
    try:
        safe_zone = _validate_public_text(zone, "approximate zone", maximum=180)
    except AlertSheetSafetyError:
        return fallback or "CEMAC"
    return " · ".join(part for part in (safe_zone, alert.region, alert.country) if part)


def _validate_public_text(value: str, field_name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise AlertSheetSafetyError(f"Alert-sheet {field_name} is invalid.")
    text = value.strip()
    if GPS_COORDINATE_PATTERN.search(text):
        raise AlertSheetSafetyError(f"Alert-sheet {field_name} must not include exact GPS coordinates.")
    if PUBLIC_CONTACT_PATTERN.search(text):
        raise AlertSheetSafetyError(f"Alert-sheet {field_name} must not include a private contact number.")
    if PRECISE_ADDRESS_PATTERN.search(text):
        raise AlertSheetSafetyError(f"Alert-sheet {field_name} must not include a precise address.")
    return text


def _normalise_datetime(value: datetime) -> datetime:
    """Treat SQLite naive timestamps as UTC before external formatting."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


__all__ = [
    "ALERT_SHEET_SCHEMA",
    "ALERT_SHEET_SCHEMA_VERSION",
    "ALERT_SHEET_SOURCE",
    "AlertSheetSafetyError",
    "build_alert_sheet",
    "validate_alert_sheet",
]
