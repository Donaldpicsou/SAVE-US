"""Versioned structured contract for SAVE-US missing-person AI reviews.

This module intentionally contains no model call.  T14 supplies deterministic
responses and T15 sends this exact input/output contract to the OpenAI API.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import Alert, AlertType, MissingPersonDetails


AI_REVIEW_SCHEMA_VERSION = "save-us.ai-review.v1"
REVIEW_DECISIONS = frozenset({"needs_information", "publish_candidate", "needs_moderation", "blocked"})
MISSING_PERSON_FIELD_NAMES = frozenset(
    {
        "name",
        "age",
        "sex",
        "photo",
        "last_seen_at",
        "last_seen_location",
        "private_family_contact",
    }
)

AI_REVIEW_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "report", "duplicate_search_scope"],
    "properties": {
        "schema_version": {"enum": [AI_REVIEW_SCHEMA_VERSION]},
        "report": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "alert_id", "alert_type", "country", "region", "approximate_zone",
                "details", "photo_available", "private_family_contact_available",
            ],
            "properties": {
                "alert_id": {"type": "string"},
                "alert_type": {"enum": [AlertType.MISSING_PERSON.value]},
                "country": {"type": "string"},
                "region": {"type": ["string", "null"]},
                "approximate_zone": {"type": ["string", "null"]},
                "photo_available": {"type": "boolean"},
                "private_family_contact_available": {"type": "boolean"},
                "details": {"type": "object"},
            },
        },
        "duplicate_search_scope": {
            "type": "object",
            "additionalProperties": False,
            "required": ["country", "alert_type", "active_statuses"],
            "properties": {
                "country": {"type": "string"},
                "alert_type": {"enum": [AlertType.MISSING_PERSON.value]},
                "active_statuses": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

AI_REVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "public_summary", "extracted_data", "missing_fields",
        "duplicate_candidates", "confidence_score", "fraud_risk_score", "decision", "reasons",
    ],
    "properties": {
        "schema_version": {"enum": [AI_REVIEW_SCHEMA_VERSION]},
        "public_summary": {"type": "string", "minLength": 1, "maxLength": 1000},
        "extracted_data": {"type": "object"},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "duplicate_candidates": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["alert_id", "similarity_score", "matching_factors"],
                "properties": {
                    "alert_id": {"type": "string"},
                    "similarity_score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "matching_factors": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "fraud_risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "decision": {"type": "string", "enum": sorted(REVIEW_DECISIONS)},
        "reasons": {"type": "array", "items": {"type": "string"}},
    },
}


class AIContractValidationError(ValueError):
    """Raised when an AI response does not respect the SAVE-US review contract."""


def build_missing_person_review_input(alert: Alert) -> dict[str, Any]:
    """Build the server-only input payload without exposing family contact details."""
    if alert.alert_type != AlertType.MISSING_PERSON:
        raise ValueError("The missing-person AI contract only accepts missing-person alerts.")
    details = alert.missing_person_details
    if details is None:
        raise ValueError("Missing-person details are required to build an AI review input.")
    return {
        "schema_version": AI_REVIEW_SCHEMA_VERSION,
        "report": {
            "alert_id": alert.id,
            "alert_type": AlertType.MISSING_PERSON.value,
            "country": alert.country,
            "region": alert.region,
            "approximate_zone": alert.approximate_zone,
            "photo_available": bool(details.photo_path),
            "private_family_contact_available": bool(details.private_family_contact),
            "details": _serialise_missing_person_details(details),
        },
        "duplicate_search_scope": {
            "country": alert.country,
            "alert_type": AlertType.MISSING_PERSON.value,
            "active_statuses": ["ai_review", "needs_moderation", "published"],
        },
    }


def validate_ai_review_output(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalise a structured AI result before it reaches the UI or DB."""
    if not isinstance(payload, Mapping):
        raise AIContractValidationError("AI review output must be a JSON object.")
    expected_keys = set(AI_REVIEW_OUTPUT_SCHEMA["required"])
    actual_keys = set(payload)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        message = []
        if missing:
            message.append(f"missing keys: {', '.join(missing)}")
        if unexpected:
            message.append(f"unexpected keys: {', '.join(unexpected)}")
        raise AIContractValidationError("Invalid AI review output (" + "; ".join(message) + ").")
    if payload["schema_version"] != AI_REVIEW_SCHEMA_VERSION:
        raise AIContractValidationError("Unsupported AI review schema version.")

    public_summary = payload["public_summary"]
    if not isinstance(public_summary, str) or not public_summary.strip() or len(public_summary) > 1000:
        raise AIContractValidationError("public_summary must be a non-empty string of 1000 characters or fewer.")
    if not isinstance(payload["extracted_data"], Mapping):
        raise AIContractValidationError("extracted_data must be an object.")
    missing_fields = _validate_string_list(payload["missing_fields"], "missing_fields")
    if not set(missing_fields).issubset(MISSING_PERSON_FIELD_NAMES):
        raise AIContractValidationError("missing_fields contains an unsupported field name.")
    duplicates = _validate_duplicates(payload["duplicate_candidates"])
    confidence_score = _validate_score(payload["confidence_score"], "confidence_score")
    fraud_risk_score = _validate_score(payload["fraud_risk_score"], "fraud_risk_score")
    decision = payload["decision"]
    if decision not in REVIEW_DECISIONS:
        raise AIContractValidationError("decision is not supported by the SAVE-US review contract.")
    reasons = _validate_string_list(payload["reasons"], "reasons")
    if not reasons:
        raise AIContractValidationError("reasons must explain the AI review decision.")

    return {
        "schema_version": AI_REVIEW_SCHEMA_VERSION,
        "public_summary": public_summary.strip(),
        "extracted_data": dict(payload["extracted_data"]),
        "missing_fields": missing_fields,
        "duplicate_candidates": duplicates,
        "confidence_score": confidence_score,
        "fraud_risk_score": fraud_risk_score,
        "decision": decision,
        "reasons": reasons,
    }


def _serialise_missing_person_details(details: MissingPersonDetails) -> dict[str, Any]:
    """Return review-relevant information; private contact remains outside the AI payload."""
    return {
        "name": details.name,
        "age": details.age,
        "sex": details.sex,
        "last_seen_at": details.last_seen_at.isoformat() if details.last_seen_at else None,
        "last_seen_location": details.last_seen_location,
        "clothing_description": details.clothing_description,
        "circumstances": details.circumstances,
    }


def _validate_score(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise AIContractValidationError(f"{field_name} must be an integer from 0 to 100.")
    return value


def _validate_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AIContractValidationError(f"{field_name} must be a list of non-empty strings.")
    return [item.strip() for item in value]


def _validate_duplicates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 10:
        raise AIContractValidationError("duplicate_candidates must contain at most 10 candidates.")
    normalised: list[dict[str, Any]] = []
    for candidate in value:
        if not isinstance(candidate, Mapping) or set(candidate) != {"alert_id", "similarity_score", "matching_factors"}:
            raise AIContractValidationError("Each duplicate candidate has an invalid shape.")
        alert_id = candidate["alert_id"]
        if not isinstance(alert_id, str) or not alert_id.strip():
            raise AIContractValidationError("A duplicate candidate needs an alert_id.")
        normalised.append(
            {
                "alert_id": alert_id.strip(),
                "similarity_score": _validate_score(candidate["similarity_score"], "duplicate similarity_score"),
                "matching_factors": _validate_string_list(candidate["matching_factors"], "matching_factors"),
            }
        )
    return normalised


__all__ = [
    "AI_REVIEW_INPUT_SCHEMA",
    "AI_REVIEW_OUTPUT_SCHEMA",
    "AI_REVIEW_SCHEMA_VERSION",
    "AIContractValidationError",
    "REVIEW_DECISIONS",
    "build_missing_person_review_input",
    "validate_ai_review_output",
]
