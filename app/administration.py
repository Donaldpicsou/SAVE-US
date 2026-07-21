"""Small, private administration-model helpers for later T42–T47 workflows."""

from __future__ import annotations

from typing import Any

from .extensions import db
from .models import AdministrationAuditEntry, SAFETY_RULE_SPECS, SafetyRule, SafetyRuleKey


def ensure_default_safety_rules() -> list[SafetyRule]:
    """Create missing bounded settings without changing existing admin choices."""
    rules: list[SafetyRule] = []
    for key, specification in SAFETY_RULE_SPECS.items():
        rule = db.session.scalar(db.select(SafetyRule).where(SafetyRule.key == key))
        if rule is None:
            rule = SafetyRule(key=key, value=specification["default"])
            db.session.add(rule)
        rules.append(rule)
    db.session.flush()
    return rules


def configured_safety_rule_values() -> dict[SafetyRuleKey, int]:
    """Return persisted rule values, falling back to bounded defaults if needed.

    This helper is used only when a new decision is made.  Published alerts keep
    their persisted status and expiry timestamp, so a later rule change cannot
    rewrite history.
    """
    rules = ensure_default_safety_rules()
    return {rule.key: rule.value for rule in rules}


def record_administration_audit(
    *,
    actor_id: int,
    action: str,
    reason: str,
    prior_value: Any = None,
    new_value: Any = None,
    target_user_id: int | None = None,
    alert_id: str | None = None,
    hospital_verification_request_id: str | None = None,
    moderator_access_request_id: str | None = None,
) -> AdministrationAuditEntry:
    """Stage one validated immutable entry; the caller controls its transaction."""
    entry = AdministrationAuditEntry(
        actor_id=actor_id,
        action=action,
        reason=reason,
        prior_value=prior_value,
        new_value=new_value,
        target_user_id=target_user_id,
        alert_id=alert_id,
        hospital_verification_request_id=hospital_verification_request_id,
        moderator_access_request_id=moderator_access_request_id,
    )
    errors = entry.validation_errors()
    if errors:
        raise ValueError(next(iter(errors.values())))
    db.session.add(entry)
    return entry


__all__ = ["configured_safety_rule_values", "ensure_default_safety_rules", "record_administration_audit"]
