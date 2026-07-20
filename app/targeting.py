"""Preference-aware recipient selection for published SAVE-US alerts."""

from __future__ import annotations

from collections.abc import Iterable

from .models import Alert, AlertStatus, AlertType, User


# PRD section 7: these categories are relevant only to the alert's region.
REGION_TARGETED_ALERT_TYPES = frozenset(
    {AlertType.MISSING_PERSON, AlertType.ROAD_ACCIDENT}
)
# PRD section 7: these high-priority/sensitive categories reach the whole country.
COUNTRY_TARGETED_ALERT_TYPES = frozenset(
    {AlertType.SUSPECTED_ABDUCTION, AlertType.UNKNOWN_HOSPITAL_PATIENT}
)


def user_receives_alert(user: User, alert: Alert) -> bool:
    """Return whether one verified subscriber should receive one public alert.

    An explicit category opt-out always wins.  Regional alerts require the
    primary or an additionally followed region; country-wide alert types do
    not.  Unpublished alerts are never returned to subscribers.
    """
    if not user.is_phone_verified or alert.status != AlertStatus.PUBLISHED:
        return False
    if user.country != alert.country:
        return False

    preference = user.alert_preference
    if preference is None or alert.alert_type.value not in set(preference.enabled_categories):
        return False

    if alert.alert_type in COUNTRY_TARGETED_ALERT_TYPES:
        return True
    if alert.alert_type in REGION_TARGETED_ALERT_TYPES:
        # A region-less regional alert is not safely targetable until a moderator corrects it.
        if not alert.region:
            return False
        return alert.region == user.primary_region or alert.region in set(preference.followed_regions)
    return False


def eligible_recipients(alert: Alert, users: Iterable[User]) -> list[User]:
    """Select the unique users eligible for a published alert in stable order."""
    recipients: list[User] = []
    seen_user_ids: set[int] = set()
    for user in users:
        if user.id in seen_user_ids or not user_receives_alert(user, alert):
            continue
        recipients.append(user)
        seen_user_ids.add(user.id)
    return recipients


__all__ = [
    "COUNTRY_TARGETED_ALERT_TYPES",
    "REGION_TARGETED_ALERT_TYPES",
    "eligible_recipients",
    "user_receives_alert",
]
