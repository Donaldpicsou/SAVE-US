"""Creation helpers for targeted in-app notifications and simulated e-mail delivery."""

from __future__ import annotations

from collections.abc import Iterable

from .extensions import db
from .models import Alert, AlertStatus, Notification, User
from .targeting import eligible_recipients


def queue_notification(
    recipient: User,
    *,
    alert: Alert | None,
    kind: str,
    title: str,
    body: str,
    public_location: str | None = None,
) -> Notification:
    """Queue one private in-app item and record whether demo e-mail was requested."""
    preference = recipient.alert_preference
    email_delivery_status = "simulated_sent" if preference and preference.email_notifications_enabled else "not_requested"
    notification = Notification(
        recipient=recipient,
        alert=alert,
        kind=kind,
        title=title,
        body=body,
        public_location=public_location,
        channel="in_app",
        email_delivery_status=email_delivery_status,
    )
    db.session.add(notification)
    return notification


def queue_review_outcome_notifications(alert: Alert) -> list[Notification]:
    """Notify eligible subscribers on publication and always notify the report owner of review status."""
    location = _public_location(alert)
    notifications: list[Notification] = []
    if alert.status == AlertStatus.PUBLISHED:
        users = db.session.scalars(db.select(User).where(User.is_phone_verified.is_(True))).all()
        for recipient in eligible_recipients(alert, users):
            if recipient.id == alert.reporter_id:
                continue
            notifications.append(
                queue_notification(
                    recipient,
                    alert=alert,
                    kind="alert_published",
                    title=f"New {alert.alert_type.value.replace('_', ' ')} alert",
                    body=alert.public_summary or alert.title,
                    public_location=location,
                )
            )
        notifications.append(
            queue_notification(
                alert.reporter,
                alert=alert,
                kind="report_published",
                title="Your report was published",
                body="Your report now appears in the eligible community alert feed.",
                public_location=location,
            )
        )
    elif alert.status == AlertStatus.NEEDS_MODERATION:
        notifications.append(
            queue_notification(
                alert.reporter,
                alert=alert,
                kind="report_needs_moderation",
                title="Your report needs moderator review",
                body="Your report was not published automatically. Open the review to see the next steps.",
                public_location=location,
            )
        )
    return notifications


def queue_closure_notifications(alert: Alert, recipients: Iterable[User], *, action: str) -> list[Notification]:
    """Notify former eligible recipients that a published alert is no longer active."""
    if action not in {"reported_found", "withdrawn"}:
        raise ValueError("Unsupported report closure notification action.")
    title = "Person reported found" if action == "reported_found" else "Alert withdrawn"
    body = (
        "The reporter marked this person as found. This alert is no longer active."
        if action == "reported_found"
        else "The reporter withdrew this alert. This alert is no longer active."
    )
    notifications = []
    for recipient in recipients:
        if recipient.id == alert.reporter_id:
            continue
        notifications.append(
            queue_notification(
                recipient,
                alert=alert,
                kind=action,
                title=title,
                body=body,
                public_location=_public_location(alert),
            )
        )
    return notifications


def _public_location(alert: Alert) -> str:
    return " · ".join(part for part in (alert.approximate_zone, alert.region, alert.country) if part)


__all__ = [
    "queue_closure_notifications",
    "queue_notification",
    "queue_review_outcome_notifications",
]
