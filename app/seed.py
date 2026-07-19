"""Idempotent demo data seed for SAVE-US local development."""

from __future__ import annotations

from collections.abc import Sequence

from .extensions import db
from .models import AlertPreference, AlertType, User, UserRole


DEMO_USERS: Sequence[dict] = (
    {
        "phone_number": "+237612345678",
        "display_name": "Amina N.",
        "role": UserRole.REPORTER,
        "country": "Cameroon",
        "primary_region": "Centre",
        "enabled_categories": [AlertType.MISSING_PERSON.value, AlertType.SUSPECTED_ABDUCTION.value],
        "followed_regions": ["Littoral"],
    },
    {
        "phone_number": "+237677123456",
        "display_name": "David T.",
        "role": UserRole.CITIZEN,
        "country": "Cameroon",
        "primary_region": "Centre",
        "enabled_categories": [AlertType.MISSING_PERSON.value, AlertType.ROAD_ACCIDENT.value],
        "followed_regions": [],
    },
    {
        "phone_number": "+237699112233",
        "display_name": "Dr. Mireille N.",
        "role": UserRole.HOSPITAL_REPRESENTATIVE,
        "country": "Cameroon",
        "primary_region": "Centre",
        "enabled_categories": [AlertType.UNKNOWN_HOSPITAL_PATIENT.value],
        "followed_regions": [],
    },
    {
        "phone_number": "+237655334455",
        "display_name": "Clarisse M.",
        "role": UserRole.MODERATOR,
        "country": "Cameroon",
        "primary_region": "Centre",
        "enabled_categories": [alert_type.value for alert_type in AlertType],
        "followed_regions": ["Littoral", "Ouest"],
    },
    {
        "phone_number": "+237688445566",
        "display_name": "Jonas K.",
        "role": UserRole.CITIZEN,
        "country": "Cameroon",
        "primary_region": "Littoral",
        "enabled_categories": [AlertType.MISSING_PERSON.value, AlertType.ROAD_ACCIDENT.value],
        "followed_regions": ["Centre"],
    },
    {
        "phone_number": "+24174001122",
        "display_name": "Paul E.",
        "role": UserRole.CITIZEN,
        "country": "Gabon",
        "primary_region": "Estuaire",
        "enabled_categories": [AlertType.MISSING_PERSON.value, AlertType.UNKNOWN_HOSPITAL_PATIENT.value],
        "followed_regions": ["Moyen-Ogooué"],
    },
    {
        "phone_number": "+237690001122",
        "display_name": "SAVE-US Admin",
        "role": UserRole.ADMINISTRATOR,
        "country": "Cameroon",
        "primary_region": "Centre",
        "enabled_categories": [alert_type.value for alert_type in AlertType],
        "followed_regions": [],
    },
)


def seed_demo_data() -> tuple[int, int]:
    """Create missing demo users and preferences; return created record counts."""
    users_created = 0
    preferences_created = 0

    for specification in DEMO_USERS:
        user = db.session.scalar(
            db.select(User).where(User.phone_number == specification["phone_number"])
        )
        if user is None:
            user = User(
                phone_number=specification["phone_number"],
                display_name=specification["display_name"],
                role=specification["role"],
                is_phone_verified=True,
                country=specification["country"],
                primary_region=specification["primary_region"],
            )
            db.session.add(user)
            db.session.flush()
            users_created += 1

        if user.alert_preference is None:
            db.session.add(
                AlertPreference(
                    user=user,
                    enabled_categories=specification["enabled_categories"],
                    followed_regions=specification["followed_regions"],
                    email_notifications_enabled=True,
                )
            )
            preferences_created += 1

    db.session.commit()
    return users_created, preferences_created
