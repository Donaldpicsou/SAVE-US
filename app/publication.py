"""Server-side safety rule that decides whether a reviewed alert can be public."""

from __future__ import annotations

from dataclasses import dataclass

from .models import AIReview, Alert, AlertStatus, utc_now


MINIMUM_PUBLICATION_CONFIDENCE = 80
MAXIMUM_PUBLICATION_FRAUD_RISK = 80


@dataclass(frozen=True)
class PublicationDecision:
    """The audit-friendly result of applying SAVE-US publication safeguards."""

    status: AlertStatus
    reason: str

    @property
    def is_published(self) -> bool:
        return self.status == AlertStatus.PUBLISHED


def decide_publication(review: AIReview) -> PublicationDecision:
    """Apply the PRD thresholds and safety blocks to a validated review.

    A fraud risk of 80 or more prevents publication.  A confidence score below
    80 also needs human review.  Possible duplicates and missing data are
    additional explicit safety conditions from the PRD, even when scores pass.
    """
    if review.fraud_risk_score >= MAXIMUM_PUBLICATION_FRAUD_RISK:
        return PublicationDecision(
            AlertStatus.NEEDS_MODERATION,
            "Publication is blocked because the fraud-risk score requires moderator review.",
        )
    if review.confidence_score < MINIMUM_PUBLICATION_CONFIDENCE:
        return PublicationDecision(
            AlertStatus.NEEDS_MODERATION,
            "Publication is paused because the confidence score is below the required threshold.",
        )
    if review.missing_fields:
        return PublicationDecision(
            AlertStatus.NEEDS_MODERATION,
            "Publication is paused until a moderator resolves the missing information.",
        )
    if review.duplicate_candidates:
        return PublicationDecision(
            AlertStatus.NEEDS_MODERATION,
            "Publication is paused because a possible duplicate needs moderator review.",
        )
    return PublicationDecision(
        AlertStatus.PUBLISHED,
        "This alert meets the publication and safety thresholds.",
    )


def apply_publication_decision(alert: Alert, review: AIReview) -> PublicationDecision:
    """Persist the publication state and expose a summary only for public alerts."""
    decision = decide_publication(review)
    alert.status = decision.status
    if decision.is_published:
        alert.published_at = utc_now()
        alert.public_summary = review.public_summary
    else:
        alert.published_at = None
        alert.public_summary = None
    return decision


__all__ = [
    "MAXIMUM_PUBLICATION_FRAUD_RISK",
    "MINIMUM_PUBLICATION_CONFIDENCE",
    "PublicationDecision",
    "apply_publication_decision",
    "decide_publication",
]
