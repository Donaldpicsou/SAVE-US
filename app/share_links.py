"""Lifecycle helpers for opaque, revocable SAVE-US external share links."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from .extensions import db
from .models import Alert, AlertShareLink, AlertStatus, utc_now


DEFAULT_SHARE_LINK_TTL = timedelta(days=7)


def create_or_get_active_share_link(alert: Alert, *, created_by_id: int, now: datetime | None = None) -> AlertShareLink:
    """Return one active opaque link for a published alert, or create a new one."""
    reference_time = _normalise_datetime(now or utc_now())
    if alert.status != AlertStatus.PUBLISHED:
        raise ValueError("Only published alerts can receive a share link.")
    existing_links = db.session.scalars(
        db.select(AlertShareLink)
        .where(AlertShareLink.alert_id == alert.id)
        .order_by(AlertShareLink.created_at.desc())
    ).all()
    for link in existing_links:
        if is_share_link_active(link, now=reference_time):
            return link

    expires_at = share_link_expiry_for(alert, now=reference_time)
    if expires_at <= reference_time:
        raise ValueError("An expired alert cannot receive a share link.")
    link = AlertShareLink(
        alert=alert,
        created_by_id=created_by_id,
        token=secrets.token_urlsafe(32),
        expires_at=expires_at,
    )
    db.session.add(link)
    db.session.commit()
    return link


def share_link_expiry_for(alert: Alert, *, now: datetime | None = None) -> datetime:
    """Use a bounded default TTL and never outlive a time-limited alert."""
    reference_time = _normalise_datetime(now or utc_now())
    expiration = reference_time + DEFAULT_SHARE_LINK_TTL
    if alert.expires_at:
        alert_expiry = _normalise_datetime(alert.expires_at)
        expiration = min(expiration, alert_expiry)
    return expiration


def is_share_link_active(link: AlertShareLink, *, now: datetime | None = None) -> bool:
    """A link becomes unusable when revoked, expired, or its alert stops being public."""
    reference_time = _normalise_datetime(now or utc_now())
    if link.revoked_at is not None or link.alert.status != AlertStatus.PUBLISHED:
        return False
    if link.alert.expires_at and _normalise_datetime(link.alert.expires_at) <= reference_time:
        return False
    return _normalise_datetime(link.expires_at) > reference_time


def revoke_share_link(link: AlertShareLink, *, now: datetime | None = None) -> None:
    """Revoke a link without deleting its accountability record."""
    if link.revoked_at is None:
        link.revoked_at = _normalise_datetime(now or utc_now())
        db.session.commit()


def _normalise_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


__all__ = [
    "DEFAULT_SHARE_LINK_TTL",
    "create_or_get_active_share_link",
    "is_share_link_active",
    "revoke_share_link",
    "share_link_expiry_for",
]
