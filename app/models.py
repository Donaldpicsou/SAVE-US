"""Core SQLAlchemy entities for SAVE-US.

Detailed report fields, AI reviews, media, notifications, and reporter actions
are added in subsequent roadmap tasks. These models establish the shared
identity, targeting, and alert lifecycle foundation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import CheckConstraint, Float, JSON, Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for lifecycle fields."""
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    """Primary user roles available in the MVP."""

    CITIZEN = "citizen"
    REPORTER = "reporter"
    HOSPITAL_REPRESENTATIVE = "hospital_representative"
    MODERATOR = "moderator"
    ADMINISTRATOR = "administrator"


class AlertType(str, Enum):
    """The four PRD alert categories."""

    MISSING_PERSON = "missing_person"
    SUSPECTED_ABDUCTION = "suspected_abduction"
    UNKNOWN_HOSPITAL_PATIENT = "unknown_hospital_patient"
    ROAD_ACCIDENT = "road_accident"


class AlertStatus(str, Enum):
    """The public and internal stages of an alert lifecycle."""

    DRAFT = "draft"
    AI_REVIEW = "ai_review"
    NEEDS_MODERATION = "needs_moderation"
    PUBLISHED = "published"
    REJECTED = "rejected"
    REPORTED_FOUND = "reported_found"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class MissingPersonSex(str, Enum):
    """Sex values used to describe a missing person in the MVP report form."""

    FEMALE = "female"
    MALE = "male"
    INTERSEX = "intersex"
    UNKNOWN = "unknown"


class User(db.Model):
    """A platform identity authenticated by a verified telephone number."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, native_enum=False, length=32),
        nullable=False,
        default=UserRole.CITIZEN,
    )
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    primary_region: Mapped[str] = mapped_column(String(120), nullable=False)
    contribution_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    alert_preference: Mapped["AlertPreference | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    submitted_alerts: Mapped[list["Alert"]] = relationship(
        back_populates="reporter",
        foreign_keys="Alert.reporter_id",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="recipient",
        cascade="all, delete-orphan",
        foreign_keys="Notification.recipient_id",
        order_by="Notification.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<User {self.id} {self.phone_number}>"


class AlertPreference(db.Model):
    """A user's opt-in alert categories and additional followed regions."""

    __tablename__ = "alert_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    enabled_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    followed_regions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped[User] = relationship(back_populates="alert_preference")

    def __repr__(self) -> str:
        return f"<AlertPreference user_id={self.user_id}>"


class Alert(db.Model):
    """A geo-targeted emergency alert submitted through SAVE-US."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_country_region_status", "country", "region", "status"),
        Index("ix_alerts_type_status", "alert_type", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    alert_type: Mapped[AlertType] = mapped_column(
        SqlEnum(AlertType, native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    status: Mapped[AlertStatus] = mapped_column(
        SqlEnum(AlertStatus, native_enum=False, length=32),
        nullable=False,
        default=AlertStatus.DRAFT,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    public_summary: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(120), index=True)
    approximate_zone: Mapped[str | None] = mapped_column(String(180))
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    reporter: Mapped[User] = relationship(
        back_populates="submitted_alerts",
        foreign_keys=[reporter_id],
    )
    missing_person_details: Mapped["MissingPersonDetails | None"] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        uselist=False,
    )
    suspected_abduction_details: Mapped["SuspectedAbductionDetails | None"] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        uselist=False,
    )
    road_accident_details: Mapped["RoadAccidentDetails | None"] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        uselist=False,
    )
    ai_review: Mapped["AIReview | None"] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        uselist=False,
    )
    report_actions: Mapped[list["ReportAction"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="ReportAction.created_at.desc()",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Alert {self.id} {self.alert_type.value} {self.status.value}>"


class MissingPersonDetails(db.Model):
    """Private reporting details attached to exactly one missing-person alert.

    Fields intentionally remain nullable while a report is a draft.  The
    ``validation_errors`` method is the single rule set used before a draft can
    progress to AI review or publication; it prevents incomplete reports from
    being submitted while allowing reporters to save their work during T11.
    """

    __tablename__ = "missing_person_details"
    __table_args__ = (
        CheckConstraint("age IS NULL OR (age >= 0 AND age <= 125)", name="ck_missing_person_age_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(180))
    age: Mapped[int | None] = mapped_column()
    sex: Mapped[str | None] = mapped_column(String(16))
    photo_path: Mapped[str | None] = mapped_column(String(500))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_location: Mapped[str | None] = mapped_column(String(255))
    clothing_description: Mapped[str | None] = mapped_column(Text)
    private_family_contact: Mapped[str | None] = mapped_column(String(64))
    circumstances: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    alert: Mapped[Alert] = relationship(back_populates="missing_person_details")

    def validation_errors(self, *, now: datetime | None = None) -> dict[str, str]:
        """Return required-field and safety errors before a report is submitted."""
        errors: dict[str, str] = {}
        reference_time = now or utc_now()

        if not self.name or not self.name.strip():
            errors["name"] = "Name is required."
        if self.age is None:
            errors["age"] = "Age is required."
        elif not 0 <= self.age <= 125:
            errors["age"] = "Age must be between 0 and 125."
        if self.sex not in {item.value for item in MissingPersonSex}:
            errors["sex"] = "Choose a valid sex."
        if not self.photo_path:
            errors["photo"] = "A photo is required."
        if self.last_seen_at is None:
            errors["last_seen_at"] = "Last-seen date and time are required."
        else:
            # SQLite may return a naive datetime despite the timezone-aware
            # column declaration; SAVE-US treats stored timestamps as UTC.
            last_seen_at = self.last_seen_at
            if last_seen_at.tzinfo is None:
                last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=timezone.utc)
            if last_seen_at > reference_time:
                errors["last_seen_at"] = "Last-seen date and time cannot be in the future."
        if not self.last_seen_location or not self.last_seen_location.strip():
            errors["last_seen_location"] = "Last-seen location is required."
        if not self.private_family_contact or not self.private_family_contact.strip():
            errors["private_family_contact"] = "A private family contact is required."
        return errors

    @property
    def is_submission_ready(self) -> bool:
        """Whether all mandatory missing-person fields are available and valid."""
        return not self.validation_errors()

    def __repr__(self) -> str:
        return f"<MissingPersonDetails alert_id={self.alert_id}>"


class SuspectedAbductionDetails(db.Model):
    """Private evidence and contact data for one suspected-abduction report.

    Every field stays nullable for a draft.  The category-specific form in T27
    will call ``validation_errors`` before handing a report to the abduction AI
    review in T28, ensuring this data never mixes with missing-person details.
    """

    __tablename__ = "suspected_abduction_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    photo_path: Mapped[str | None] = mapped_column(String(500))
    abduction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    circumstances: Mapped[str | None] = mapped_column(Text)
    private_contact: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    alert: Mapped[Alert] = relationship(back_populates="suspected_abduction_details")

    def validation_errors(self, *, now: datetime | None = None, require_photo: bool = False) -> dict[str, str]:
        """Return required-field and timing errors before an abduction review."""
        errors: dict[str, str] = {}
        reference_time = now or utc_now()

        if self.alert.alert_type != AlertType.SUSPECTED_ABDUCTION:
            errors["alert_type"] = "Abduction details require a suspected-abduction alert."
        if require_photo and not self.photo_path:
            errors["photo"] = "A photo is required."
        if self.abduction_at is None:
            errors["abduction_at"] = "Abduction date and time are required."
        else:
            abduction_at = self.abduction_at
            if abduction_at.tzinfo is None:
                abduction_at = abduction_at.replace(tzinfo=timezone.utc)
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=timezone.utc)
            if abduction_at > reference_time:
                errors["abduction_at"] = "Abduction date and time cannot be in the future."
        if not self.alert.approximate_zone or not self.alert.approximate_zone.strip():
            errors["approximate_zone"] = "An approximate public area is required."
        if not self.description or not self.description.strip():
            errors["description"] = "A description is required."
        if not self.circumstances or not self.circumstances.strip():
            errors["circumstances"] = "Circumstances are required."
        if not self.private_contact or not self.private_contact.strip():
            errors["private_contact"] = "A private contact is required."
        return errors

    @property
    def is_submission_ready(self) -> bool:
        """Whether the suspected-abduction report is ready for its future AI review."""
        return not self.validation_errors()

    def __repr__(self) -> str:
        return f"<SuspectedAbductionDetails alert_id={self.alert_id}>"


class RoadAccidentDetails(db.Model):
    """Private operational facts for one road-accident alert.

    The parent alert continues to own country/region targeting.  The affected
    region is stored here too as the report-specific declaration and is checked
    against the parent before submission, preventing a targeting mismatch.
    All fields remain nullable while T31 is saving a draft.
    """

    __tablename__ = "road_accident_details"
    __table_args__ = (
        CheckConstraint("victim_count IS NULL OR victim_count >= 0", name="ck_road_accident_victim_count_nonnegative"),
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_road_accident_latitude_range"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_road_accident_longitude_range"),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_road_accident_coordinate_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manual_location: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    affected_region: Mapped[str | None] = mapped_column(String(120))
    victim_count: Mapped[int | None] = mapped_column()
    immediate_needs: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    media_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    alert: Mapped[Alert] = relationship(back_populates="road_accident_details")

    def validation_errors(self, *, now: datetime | None = None) -> dict[str, str]:
        """Return the rules T31 will use before a road-accident report is submitted."""
        errors: dict[str, str] = {}
        reference_time = now or utc_now()
        if self.alert.alert_type != AlertType.ROAD_ACCIDENT:
            errors["alert_type"] = "Road-accident details require a road-accident alert."
        if self.occurred_at is None:
            errors["occurred_at"] = "Accident date and time are required."
        else:
            occurred_at = self.occurred_at.replace(tzinfo=timezone.utc) if self.occurred_at.tzinfo is None else self.occurred_at
            reference_time = reference_time.replace(tzinfo=timezone.utc) if reference_time.tzinfo is None else reference_time
            if occurred_at > reference_time:
                errors["occurred_at"] = "Accident date and time cannot be in the future."
        if not self.manual_location or not self.manual_location.strip():
            errors["manual_location"] = "A manual accident location is required."
        if not self.affected_region or not self.affected_region.strip():
            errors["affected_region"] = "The affected region is required."
        elif self.alert.region and self.affected_region != self.alert.region:
            errors["affected_region"] = "The affected region must match the alert region."
        if (self.latitude is None) != (self.longitude is None):
            errors["coordinates"] = "Latitude and longitude must be provided together."
        elif self.latitude is not None and not -90 <= self.latitude <= 90:
            errors["latitude"] = "Latitude must be between -90 and 90."
        elif self.longitude is not None and not -180 <= self.longitude <= 180:
            errors["longitude"] = "Longitude must be between -180 and 180."
        if self.victim_count is not None and self.victim_count < 0:
            errors["victim_count"] = "Victim count cannot be negative."
        if not self.description or not self.description.strip():
            errors["description"] = "An accident description is required."
        if self.media_references is not None and (
            not isinstance(self.media_references, list)
            or not all(isinstance(item, str) and item.strip() for item in self.media_references)
        ):
            errors["media_references"] = "Media references must be a list of non-empty values."
        return errors

    @property
    def is_submission_ready(self) -> bool:
        """Whether the road-accident draft has the data required for T31 submission."""
        return not self.validation_errors()

    def __repr__(self) -> str:
        return f"<RoadAccidentDetails alert_id={self.alert_id}>"


class AIReview(db.Model):
    """A persisted, contract-validated AI review for one emergency alert."""

    __tablename__ = "ai_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    public_summary: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    missing_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    duplicate_candidates: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    confidence_score: Mapped[int] = mapped_column(nullable=False)
    fraud_risk_score: Mapped[int] = mapped_column(nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    fallback_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    alert: Mapped[Alert] = relationship(back_populates="ai_review")

    def __repr__(self) -> str:
        return f"<AIReview alert_id={self.alert_id} decision={self.decision}>"


class ReportAction(db.Model):
    """Non-public audit record for a reporter's closure or correction action."""

    __tablename__ = "report_actions"
    __table_args__ = (Index("ix_report_actions_alert_created", "alert_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    alert: Mapped[Alert] = relationship(back_populates="report_actions")
    actor: Mapped[User] = relationship(foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<ReportAction alert_id={self.alert_id} action={self.action}>"


class Notification(db.Model):
    """A private in-app notification with optional simulated e-mail delivery state."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_created", "recipient_id", "created_at"),
        Index("ix_notifications_recipient_read", "recipient_id", "is_read"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id: Mapped[str | None] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    public_location: Mapped[str | None] = mapped_column(String(180))
    channel: Mapped[str] = mapped_column(String(24), nullable=False, default="in_app")
    email_delivery_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_requested")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    recipient: Mapped[User] = relationship(back_populates="notifications", foreign_keys=[recipient_id])
    alert: Mapped[Alert | None] = relationship(back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification {self.id} recipient={self.recipient_id} kind={self.kind}>"


__all__ = [
    "Alert",
    "AlertPreference",
    "AlertStatus",
    "AlertType",
    "AIReview",
    "MissingPersonDetails",
    "MissingPersonSex",
    "Notification",
    "ReportAction",
    "RoadAccidentDetails",
    "SuspectedAbductionDetails",
    "User",
    "UserRole",
    "db",
]
