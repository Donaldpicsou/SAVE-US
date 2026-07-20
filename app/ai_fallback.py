"""Deterministic, offline AI-review fallback used for the SAVE-US demo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .ai_contract import (
    AI_REVIEW_SCHEMA_VERSION,
    MISSING_PERSON_FIELD_NAMES,
    validate_ai_review_output,
)
from .abduction_ai_contract import (
    ABDUCTION_AI_REVIEW_SCHEMA_VERSION,
    ABDUCTION_MISSING_FIELD_NAMES,
    validate_suspected_abduction_review_output,
)


FALLBACK_REVIEW_SOURCE = "deterministic_demo_fallback"

# A deliberate demo case for showing the duplicate-review state in T16.
DEMO_DUPLICATE_CATALOG = {
    "samuel mbo": {
        "alert_id": "demo-active-alert-samuel-mbo",
        "similarity_score": 91,
        "matching_factors": ["same name", "same age range", "same last-seen area"],
    },
}


def deterministic_ai_review(review_input: Mapping[str, Any]) -> dict[str, Any]:
    """Produce a stable contract-valid review when a live model is unavailable.

    It is intentionally transparent demo logic, not a claim of factual
    verification.  The same report data always yields the same output.
    """
    report = _required_mapping(review_input, "report")
    details = _required_mapping(report, "details")
    missing_fields = _missing_fields(report, details)
    name = _text(details.get("name"))
    duplicate_candidates = _duplicate_candidates(name)

    if missing_fields:
        confidence_score = max(25, 75 - 8 * len(missing_fields))
        fraud_risk_score = 20
        decision = "needs_information"
        reasons = [
            "The report is incomplete and needs the listed information before review can continue.",
            "SAVE-US does not publish an incomplete missing-person report.",
        ]
    elif duplicate_candidates:
        confidence_score = 86
        fraud_risk_score = 18
        decision = "needs_moderation"
        reasons = [
            "The report is complete, but a high-similarity active alert was found.",
            "A moderator must review a possible duplicate before publication.",
        ]
    else:
        confidence_score = 88
        fraud_risk_score = 12
        decision = "publish_candidate"
        reasons = [
            "All required missing-person fields are present.",
            "No high-similarity active alert was found by the deterministic demo check.",
        ]

    output = {
        "schema_version": AI_REVIEW_SCHEMA_VERSION,
        "public_summary": _public_summary(report, details),
        "extracted_data": {
            "name": details.get("name"),
            "age": details.get("age"),
            "sex": details.get("sex"),
            "last_seen_at": details.get("last_seen_at"),
            "last_seen_location": details.get("last_seen_location"),
            "clothing_description": details.get("clothing_description"),
            "circumstances": details.get("circumstances"),
            "photo_available": bool(report.get("photo_available")),
            "private_family_contact_available": bool(report.get("private_family_contact_available")),
        },
        "missing_fields": missing_fields,
        "duplicate_candidates": duplicate_candidates,
        "confidence_score": confidence_score,
        "fraud_risk_score": fraud_risk_score,
        "decision": decision,
        "reasons": reasons,
    }
    return validate_ai_review_output(output)


def deterministic_abduction_ai_review(review_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stable, public-safe suspected-abduction review for the demo."""
    report = _required_mapping(review_input, "report")
    details = _required_mapping(report, "details")
    checks = (
        ("title", _text(report.get("title"))),
        ("abduction_at", _text(details.get("abduction_at"))),
        ("approximate_zone", _text(report.get("approximate_zone"))),
        ("description", _text(details.get("description"))),
        ("circumstances", _text(details.get("circumstances"))),
        ("private_contact", bool(report.get("private_contact_available"))),
    )
    missing_fields = [name for name, available in checks if not available and name in ABDUCTION_MISSING_FIELD_NAMES]
    # A photo can strengthen a report but stays optional under the T26 field rules.
    if missing_fields:
        confidence_score, fraud_risk_score, decision = 65, 20, "needs_information"
        reasons = [
            "The report is incomplete and needs the listed information before it can be shared.",
            "SAVE-US does not publish an incomplete suspected-abduction report.",
        ]
    else:
        confidence_score, fraud_risk_score, decision = 88, 12, "publish_candidate"
        reasons = [
            "The required suspected-abduction report details are present.",
            "No possible duplicate was returned by the deterministic demo check.",
        ]

    area = _text(report.get("approximate_zone")) or _text(report.get("region")) or _text(report.get("country")) or "the reported area"
    output = {
        "schema_version": ABDUCTION_AI_REVIEW_SCHEMA_VERSION,
        "public_summary": f"A suspected abduction was reported near {area}. Please stay alert and share information responsibly.",
        "extracted_data": {
            "title": report.get("title"),
            "country": report.get("country"),
            "region": report.get("region"),
            "approximate_zone": report.get("approximate_zone"),
            "abduction_at": details.get("abduction_at"),
            "description": details.get("description"),
            "circumstances": details.get("circumstances"),
            "photo_available": bool(report.get("photo_available")),
            "private_contact_available": bool(report.get("private_contact_available")),
        },
        "missing_fields": missing_fields,
        "duplicate_candidates": [],
        "confidence_score": confidence_score,
        "fraud_risk_score": fraud_risk_score,
        "decision": decision,
        "reasons": reasons,
    }
    return validate_suspected_abduction_review_output(output)


def _missing_fields(report: Mapping[str, Any], details: Mapping[str, Any]) -> list[str]:
    """Return required fields in a stable order, using availability flags for private data."""
    field_checks = (
        ("name", _text(details.get("name"))),
        ("age", isinstance(details.get("age"), int) and not isinstance(details.get("age"), bool) and 0 <= details["age"] <= 125),
        ("sex", details.get("sex") in {"female", "male", "intersex", "unknown"}),
        ("photo", bool(report.get("photo_available"))),
        ("last_seen_at", _text(details.get("last_seen_at"))),
        ("last_seen_location", _text(details.get("last_seen_location"))),
        ("private_family_contact", bool(report.get("private_family_contact_available"))),
    )
    return [field for field, available in field_checks if not available and field in MISSING_PERSON_FIELD_NAMES]


def _duplicate_candidates(name: str | None) -> list[dict[str, Any]]:
    """Return a fixed catalogue match to demonstrate duplicate handling offline."""
    if not name:
        return []
    candidate = DEMO_DUPLICATE_CATALOG.get(" ".join(name.lower().split()))
    return [dict(candidate)] if candidate else []


def _public_summary(report: Mapping[str, Any], details: Mapping[str, Any]) -> str:
    """Create an English, public-safe summary without contact or precise address."""
    name = _text(details.get("name")) or "A person"
    age = details.get("age")
    age_text = f", age {age}" if isinstance(age, int) and not isinstance(age, bool) else ""
    area = _text(report.get("approximate_zone")) or _text(report.get("region")) or _text(report.get("country")) or "the reported area"
    return f"{name}{age_text} was reported missing near {area}."


def _required_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"The AI review input is missing a valid {key} object.")
    return value


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


__all__ = ["FALLBACK_REVIEW_SOURCE", "deterministic_abduction_ai_review", "deterministic_ai_review"]
