"""Idempotent demo data seed for SAVE-US local development."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw

from .administration import ensure_default_safety_rules
from .extensions import db
from .models import (
    AIReview,
    Alert,
    AlertPreference,
    AlertStatus,
    AlertType,
    HospitalVerificationRequest,
    HospitalVerificationStatus,
    MissingPersonDetails,
    ModeratorAccessRequest,
    ModeratorAccessRequestStatus,
    ReportAction,
    RoadAccidentDetails,
    RoadAccidentMediaReview,
    SuspectedAbductionDetails,
    User,
    UserRole,
    utc_now,
)
from .notification_service import (
    queue_administrator_request_notifications,
    queue_review_outcome_notifications,
)


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
    {
        "phone_number": "+237644221100",
        "display_name": "Nora B.",
        "role": UserRole.CITIZEN,
        "country": "Cameroon",
        "primary_region": "Centre",
        "enabled_categories": [AlertType.UNKNOWN_HOSPITAL_PATIENT.value],
        "followed_regions": [],
    },
)


# Stable identifiers make the local demo idempotent even when the seed command
# is run repeatedly. All names, locations, contacts, and scenarios are fictional.
DEMO_ALERT_IDS = {
    "missing": "00000000-0000-4000-8000-000000000101",
    "abduction": "00000000-0000-4000-8000-000000000102",
    "road_accident": "00000000-0000-4000-8000-000000000103",
    "moderation": "00000000-0000-4000-8000-000000000104",
}
DEMO_HOSPITAL_REQUEST_ID = "00000000-0000-4000-8000-000000000201"
DEMO_MODERATOR_REQUEST_ID = "00000000-0000-4000-8000-000000000202"


def seed_demo_data() -> tuple[int, int]:
    """Create idempotent accounts, preferences, and safe end-to-end demo scenarios."""
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

    db.session.flush()
    _seed_demo_scenarios()
    ensure_default_safety_rules()
    db.session.commit()
    return users_created, preferences_created


def _demo_user(phone_number: str) -> User:
    user = db.session.scalar(db.select(User).where(User.phone_number == phone_number))
    if user is None:
        raise RuntimeError(f"Missing expected demo user {phone_number}.")
    return user


def _ensure_fictional_demo_portrait() -> str:
    """Create a clearly fictional local illustration for the opt-in sharing demo.

    The generated PNG is a geometric avatar, not a photograph of a person. It
    stays in private upload storage until SAVE-US creates an authorised,
    metadata-free derivative for a sheet, PDF, or secure share page.
    """
    relative_path = Path("demo") / "missing-person-nadia-fictional.png"
    target = Path(current_app.config["UPLOAD_FOLDER"]) / relative_path
    if target.is_file():
        return relative_path.as_posix()

    target.parent.mkdir(parents=True, exist_ok=True)
    portrait = Image.new("RGB", (640, 640), "#e8f5ff")
    draw = ImageDraw.Draw(portrait)
    draw.ellipse((180, 105, 460, 385), fill="#8b5a3c")
    draw.arc((145, 65, 495, 430), 180, 360, fill="#07375f", width=42)
    draw.rounded_rectangle((125, 395, 515, 690), radius=110, fill="#1689c3")
    draw.ellipse((255, 220, 280, 245), fill="#07375f")
    draw.ellipse((360, 220, 385, 245), fill="#07375f")
    draw.arc((275, 255, 370, 330), 0, 180, fill="#07375f", width=10)
    portrait.save(target, format="PNG", optimize=True)
    return relative_path.as_posix()


def _seed_demo_scenarios() -> None:
    """Add fictional alert, moderation, administration, and notification examples once."""
    now = utc_now()
    reporter = _demo_user("+237612345678")
    citizen = _demo_user("+237677123456")
    moderator = _demo_user("+237655334455")
    hospital_applicant = _demo_user("+237644221100")
    newly_created_alerts: list[Alert] = []

    if db.session.get(Alert, DEMO_ALERT_IDS["missing"]) is None:
        alert = Alert(
            id=DEMO_ALERT_IDS["missing"],
            alert_type=AlertType.MISSING_PERSON,
            status=AlertStatus.PUBLISHED,
            title="Nadia E.",
            public_summary="Nadia E., age 14, was reported missing near the Mfoundi district.",
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi district",
            reporter=reporter,
            published_at=now - timedelta(minutes=35),
        )
        alert.missing_person_details = MissingPersonDetails(
            name="Nadia E.",
            age=14,
            sex="female",
            photo_path=_ensure_fictional_demo_portrait(),
            public_media_authorized=True,
            last_seen_at=now - timedelta(hours=5),
            last_seen_location="Mfoundi district",
            clothing_description="Blue jacket and dark trousers.",
            private_family_contact="Demo family contact — private",
            circumstances="Fictional demonstration record. Family requested a local community search.",
        )
        alert.ai_review = AIReview(
            public_summary=alert.public_summary,
            extracted_data={"name": "Nadia E.", "age": 14, "region": "Centre"},
            missing_fields=[],
            duplicate_candidates=[],
            confidence_score=91,
            fraud_risk_score=10,
            decision="published",
            reasons=["The fictional demo report contains the required information."],
            source="deterministic_demo",
            fallback_reason="Seeded demonstration scenario.",
        )
        db.session.add(alert)
        newly_created_alerts.append(alert)

    # Preserve the photo-sharing scenario when an earlier seed created this
    # alert before the fictional avatar was introduced.
    missing_alert = db.session.get(Alert, DEMO_ALERT_IDS["missing"])
    if missing_alert and missing_alert.missing_person_details:
        missing_alert.missing_person_details.photo_path = _ensure_fictional_demo_portrait()
        missing_alert.missing_person_details.public_media_authorized = True

    if db.session.get(Alert, DEMO_ALERT_IDS["abduction"]) is None:
        alert = Alert(
            id=DEMO_ALERT_IDS["abduction"],
            alert_type=AlertType.SUSPECTED_ABDUCTION,
            status=AlertStatus.PUBLISHED,
            title="Urgent community safety report",
            public_summary="A suspected abduction was reported near the Yaoundé transport area. Stay alert and share only verified information.",
            country="Cameroon",
            region="Centre",
            approximate_zone="Yaoundé transport area",
            reporter=reporter,
            published_at=now - timedelta(minutes=22),
        )
        alert.suspected_abduction_details = SuspectedAbductionDetails(
            abduction_at=now - timedelta(hours=2),
            description="Fictional demo report describing a concern reported near a public transport area.",
            circumstances="Fictional demonstration scenario for country-wide targeting and follow-up moderation.",
            private_contact="Demo private contact — private",
        )
        alert.ai_review = AIReview(
            public_summary=alert.public_summary,
            extracted_data={"country": "Cameroon", "approximate_zone": "Yaoundé transport area"},
            missing_fields=[],
            duplicate_candidates=[],
            confidence_score=87,
            fraud_risk_score=18,
            decision="published",
            reasons=["The fictional demo report meets the configured publication thresholds."],
            source="deterministic_demo",
            fallback_reason="Seeded demonstration scenario.",
        )
        alert.report_actions.append(
            ReportAction(
                actor_id=moderator.id,
                action="moderator_publish",
                reason="Fictional demo moderation decision recorded for the administration workspace.",
                created_at=now - timedelta(minutes=20),
            )
        )
        db.session.add(alert)
        newly_created_alerts.append(alert)

    if db.session.get(Alert, DEMO_ALERT_IDS["road_accident"]) is None:
        alert = Alert(
            id=DEMO_ALERT_IDS["road_accident"],
            alert_type=AlertType.ROAD_ACCIDENT,
            status=AlertStatus.PUBLISHED,
            title="Road safety alert near Obala",
            public_summary="A serious road accident was reported near Obala. Please use caution and contact emergency services if needed.",
            country="Cameroon",
            region="Centre",
            approximate_zone="Obala area",
            reporter=citizen,
            published_at=now - timedelta(minutes=12),
            expires_at=now + timedelta(hours=23, minutes=48),
        )
        alert.road_accident_details = RoadAccidentDetails(
            occurred_at=now - timedelta(minutes=40),
            manual_location="N4 near Obala",
            affected_region="Centre",
            victim_count=2,
            immediate_needs="Traffic caution and emergency response.",
            description="Fictional demo collision report. No media is attached or shared.",
            media_references=[],
        )
        alert.road_accident_media_review = RoadAccidentMediaReview(
            media_reference=None,
            status="clear",
            reason="No media was attached to this fictional demonstration report.",
            source="deterministic_demo",
        )
        db.session.add(alert)
        newly_created_alerts.append(alert)

    if db.session.get(Alert, DEMO_ALERT_IDS["moderation"]) is None:
        alert = Alert(
            id=DEMO_ALERT_IDS["moderation"],
            alert_type=AlertType.MISSING_PERSON,
            status=AlertStatus.NEEDS_MODERATION,
            title="Private moderation demo report",
            country="Cameroon",
            region="Centre",
            approximate_zone="Yaoundé area",
            reporter=reporter,
        )
        alert.missing_person_details = MissingPersonDetails(
            name="Maya L.",
            age=31,
            sex="female",
            last_seen_at=now - timedelta(hours=9),
            last_seen_location="Yaoundé area",
            clothing_description="Green top and black bag.",
            private_family_contact="Demo family contact — private",
            circumstances="Fictional scenario retained for moderator review because a possible duplicate needs attention.",
        )
        alert.ai_review = AIReview(
            public_summary="Maya L., age 31, was reported missing near the Yaoundé area.",
            extracted_data={"name": "Maya L.", "age": 31, "region": "Centre"},
            missing_fields=[],
            duplicate_candidates=[{"alert_id": "demo-possible-match", "reason": "Similar name and area in a fictional demo record."}],
            confidence_score=83,
            fraud_risk_score=23,
            decision="needs_moderation",
            reasons=["A possible duplicate requires a human decision before publication."],
            source="deterministic_demo",
            fallback_reason="Seeded demonstration scenario.",
        )
        db.session.add(alert)
        newly_created_alerts.append(alert)

    db.session.flush()
    for alert in newly_created_alerts:
        queue_review_outcome_notifications(alert)

    if db.session.get(HospitalVerificationRequest, DEMO_HOSPITAL_REQUEST_ID) is None:
        request = HospitalVerificationRequest(
            id=DEMO_HOSPITAL_REQUEST_ID,
            submitted_by_id=hospital_applicant.id,
            hospital_name="SAVE-US Demo Medical Centre",
            country="Cameroon",
            region="Centre",
            contact_name="Nora B.",
            contact_phone="+237644221100",
            supporting_document_reference="demo/private/hospital-verification-reference.pdf",
            status=HospitalVerificationStatus.PENDING,
        )
        db.session.add(request)
        db.session.flush()
        queue_administrator_request_notifications(
            request_type="hospital_verification",
            request_id=request.id,
            title="Hospital verification awaiting review",
            body="A fictional SAVE-US Demo Medical Centre verification request is ready for private administration review.",
        )

    if db.session.get(ModeratorAccessRequest, DEMO_MODERATOR_REQUEST_ID) is None:
        request = ModeratorAccessRequest(
            id=DEMO_MODERATOR_REQUEST_ID,
            submitted_by_id=citizen.id,
            reason="Fictional demo request to show the private, reasoned moderator-access workflow.",
            status=ModeratorAccessRequestStatus.PENDING,
        )
        db.session.add(request)
        db.session.flush()
        queue_administrator_request_notifications(
            request_type="moderator_access",
            request_id=request.id,
            title="Moderator access request awaiting review",
            body="A fictional community-member access request is ready for private administration review.",
        )
