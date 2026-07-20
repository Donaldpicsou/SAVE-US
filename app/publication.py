"""Server-side safety rule that decides whether a reviewed alert can be public."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from .extensions import db
from .models import AIReview, Alert, AlertStatus, AlertType, User, utc_now
from .notification_service import queue_expiry_notifications
from .road_media_moderation import MEDIA_STATUS_BLOCKED, MEDIA_STATUS_CLEAR, MEDIA_STATUS_NEEDS_MODERATION
from .targeting import eligible_recipients


MINIMUM_PUBLICATION_CONFIDENCE = 80
MAXIMUM_PUBLICATION_FRAUD_RISK = 80
ROAD_ACCIDENT_EXPIRY_HOURS = 24


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


def apply_road_accident_publication(alert: Alert) -> PublicationDecision:
    """Publish a complete, media-safe road accident to its affected region for 24 hours."""
    if alert.alert_type != AlertType.ROAD_ACCIDENT:
        raise ValueError("Road-accident publication only accepts road-accident alerts.")
    media_review = alert.road_accident_media_review
    if media_review is None:
        alert.status = AlertStatus.NEEDS_MODERATION
        return PublicationDecision(AlertStatus.NEEDS_MODERATION, "Publication is paused until the optional media safety check is complete.")
    if media_review.status == MEDIA_STATUS_BLOCKED:
        alert.status = AlertStatus.REJECTED
        return PublicationDecision(AlertStatus.REJECTED, media_review.reason)
    if media_review.status == MEDIA_STATUS_NEEDS_MODERATION:
        alert.status = AlertStatus.NEEDS_MODERATION
        return PublicationDecision(AlertStatus.NEEDS_MODERATION, media_review.reason)
    details = alert.road_accident_details
    if details is None or details.validation_errors():
        alert.status = AlertStatus.NEEDS_MODERATION
        return PublicationDecision(AlertStatus.NEEDS_MODERATION, "Publication is paused until a moderator resolves the report information.")
    if media_review.status != MEDIA_STATUS_CLEAR:
        alert.status = AlertStatus.NEEDS_MODERATION
        return PublicationDecision(AlertStatus.NEEDS_MODERATION, "Publication is paused for a media safety review.")

    published_at = utc_now()
    alert.status = AlertStatus.PUBLISHED
    alert.published_at = published_at
    alert.expires_at = published_at + timedelta(hours=ROAD_ACCIDENT_EXPIRY_HOURS)
    # The private manual location and optional coordinates never become public summary content.
    location = alert.approximate_zone or alert.region or alert.country
    alert.public_summary = f"A serious road accident was reported near {location}. Please use caution and contact emergency services if needed."
    return PublicationDecision(AlertStatus.PUBLISHED, "This road accident was published to eligible users in the affected region for 24 hours.")


def expire_due_road_accidents() -> list[Alert]:
    """End public regional visibility after the 24-hour accident-alert window."""
    now = utc_now()
    alerts = db.session.scalars(
        db.select(Alert).where(
            Alert.alert_type == AlertType.ROAD_ACCIDENT,
            Alert.status == AlertStatus.PUBLISHED,
            Alert.expires_at.is_not(None),
            Alert.expires_at <= now,
        )
    ).all()
    for alert in alerts:
        users = db.session.scalars(db.select(User).where(User.is_phone_verified.is_(True))).all()
        recipients = eligible_recipients(alert, users)
        alert.status = AlertStatus.EXPIRED
        queue_expiry_notifications(alert, recipients)
    if alerts:
        db.session.commit()
    return alerts


__all__ = [
    "MAXIMUM_PUBLICATION_FRAUD_RISK",
    "MINIMUM_PUBLICATION_CONFIDENCE",
    "ROAD_ACCIDENT_EXPIRY_HOURS",
    "PublicationDecision",
    "apply_road_accident_publication",
    "apply_publication_decision",
    "decide_publication",
    "expire_due_road_accidents",
]
