"""Versioned structured contract for SAVE-US suspected-abduction reviews.

This task defines data boundaries and validation only.  T29 will apply the
publication rule; no provider call or publication occurs in this module.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .ai_contract import (
    AIContractValidationError,
    REVIEW_DECISIONS,
    _validate_duplicates,
    _validate_score,
    _validate_string_list,
)
from .models import Alert, AlertType, SuspectedAbductionDetails


ABDUCTION_AI_REVIEW_SCHEMA_VERSION = "save-us.abduction-review.v1"
ABDUCTION_MISSING_FIELD_NAMES = frozenset(
    {
        "title",
        "photo",
        "abduction_at",
        "approximate_zone",
        "description",
        "circumstances",
        "private_contact",
    }
)
# A public alert summary never needs a phone number.  This rejects ordinary
# international and local-looking contact sequences while still permitting ages,
# times, and short incident identifiers.
PUBLIC_CONTACT_PATTERN = re.compile(r"(?:\+?\d[\s().-]*){7,}\d")


ABDUCTION_AI_REVIEW_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "report", "duplicate_search_scope"],
    "properties": {
        "schema_version": {"enum": [ABDUCTION_AI_REVIEW_SCHEMA_VERSION]},
        "report": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "alert_id", "alert_type", "title", "country", "region", "approximate_zone",
                "details", "photo_available", "private_contact_available",
            ],
            "properties": {
                "alert_id": {"type": "string"},
                "alert_type": {"enum": [AlertType.SUSPECTED_ABDUCTION.value]},
                "title": {"type": "string"},
                "country": {"type": "string"},
                "region": {"type": ["string", "null"]},
                "approximate_zone": {"type": ["string", "null"]},
                "photo_available": {"type": "boolean"},
                "private_contact_available": {"type": "boolean"},
                "details": {"type": "object"},
            },
        },
        "duplicate_search_scope": {
            "type": "object",
            "additionalProperties": False,
            "required": ["country", "alert_type", "active_statuses"],
            "properties": {
                "country": {"type": "string"},
                "alert_type": {"enum": [AlertType.SUSPECTED_ABDUCTION.value]},
                "active_statuses": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

ABDUCTION_AI_REVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "public_summary", "extracted_data", "missing_fields",
        "duplicate_candidates", "confidence_score", "fraud_risk_score", "decision", "reasons",
    ],
    "properties": {
        "schema_version": {"enum": [ABDUCTION_AI_REVIEW_SCHEMA_VERSION]},
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


def build_suspected_abduction_review_input(alert: Alert) -> dict[str, Any]:
    """Build a category-specific review input without private contact content."""
    if alert.alert_type != AlertType.SUSPECTED_ABDUCTION:
        raise ValueError("The abduction AI contract only accepts suspected-abduction alerts.")
    details = alert.suspected_abduction_details
    if details is None:
        raise ValueError("Suspected-abduction details are required to build an AI review input.")
    return {
        "schema_version": ABDUCTION_AI_REVIEW_SCHEMA_VERSION,
        "report": {
            "alert_id": alert.id,
            "alert_type": AlertType.SUSPECTED_ABDUCTION.value,
            "title": alert.title,
            "country": alert.country,
            "region": alert.region,
            "approximate_zone": alert.approximate_zone,
            "photo_available": bool(details.photo_path),
            "private_contact_available": bool(details.private_contact),
            "details": _serialise_suspected_abduction_details(details),
        },
        "duplicate_search_scope": {
            "country": alert.country,
            "alert_type": AlertType.SUSPECTED_ABDUCTION.value,
            "active_statuses": ["ai_review", "needs_moderation", "published"],
        },
    }


def validate_suspected_abduction_review_output(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the structured review before it can reach an alert or moderator."""
    if not isinstance(payload, Mapping):
        raise AIContractValidationError("AI review output must be a JSON object.")
    expected_keys = set(ABDUCTION_AI_REVIEW_OUTPUT_SCHEMA["required"])
    actual_keys = set(payload)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        messages = []
        if missing:
            messages.append(f"missing keys: {', '.join(missing)}")
        if unexpected:
            messages.append(f"unexpected keys: {', '.join(unexpected)}")
        raise AIContractValidationError("Invalid AI review output (" + "; ".join(messages) + ").")
    if payload["schema_version"] != ABDUCTION_AI_REVIEW_SCHEMA_VERSION:
        raise AIContractValidationError("Unsupported abduction AI review schema version.")

    public_summary = payload["public_summary"]
    if not isinstance(public_summary, str) or not public_summary.strip() or len(public_summary) > 1000:
        raise AIContractValidationError("public_summary must be a non-empty string of 1000 characters or fewer.")
    if PUBLIC_CONTACT_PATTERN.search(public_summary):
        raise AIContractValidationError("public_summary must not include a private contact number.")
    if not isinstance(payload["extracted_data"], Mapping):
        raise AIContractValidationError("extracted_data must be an object.")
    missing_fields = _validate_string_list(payload["missing_fields"], "missing_fields")
    if not set(missing_fields).issubset(ABDUCTION_MISSING_FIELD_NAMES):
        raise AIContractValidationError("missing_fields contains an unsupported field name.")
    duplicates = _validate_duplicates(payload["duplicate_candidates"])
    confidence_score = _validate_score(payload["confidence_score"], "confidence_score")
    fraud_risk_score = _validate_score(payload["fraud_risk_score"], "fraud_risk_score")
    decision = payload["decision"]
    if decision not in REVIEW_DECISIONS:
        raise AIContractValidationError("decision is not supported by the abduction AI review contract.")
    reasons = _validate_string_list(payload["reasons"], "reasons")
    if not reasons:
        raise AIContractValidationError("reasons must explain the AI review decision.")

    return {
        "schema_version": ABDUCTION_AI_REVIEW_SCHEMA_VERSION,
        "public_summary": public_summary.strip(),
        "extracted_data": dict(payload["extracted_data"]),
        "missing_fields": missing_fields,
        "duplicate_candidates": duplicates,
        "confidence_score": confidence_score,
        "fraud_risk_score": fraud_risk_score,
        "decision": decision,
        "reasons": reasons,
    }


def _serialise_suspected_abduction_details(details: SuspectedAbductionDetails) -> dict[str, Any]:
    """Return review-relevant facts while deliberately omitting private contact data."""
    return {
        "abduction_at": details.abduction_at.isoformat() if details.abduction_at else None,
        "description": details.description,
        "circumstances": details.circumstances,
    }


__all__ = [
    "ABDUCTION_AI_REVIEW_INPUT_SCHEMA",
    "ABDUCTION_AI_REVIEW_OUTPUT_SCHEMA",
    "ABDUCTION_AI_REVIEW_SCHEMA_VERSION",
    "ABDUCTION_MISSING_FIELD_NAMES",
    "AIContractValidationError",
    "build_suspected_abduction_review_input",
    "validate_suspected_abduction_review_output",
]
