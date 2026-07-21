"""Core SQLAlchemy entities for SAVE-US.

Detailed report fields, AI reviews, media, notifications, and reporter actions
are added in subsequent roadmap tasks. These models establish the shared
identity, targeting, and alert lifecycle foundation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import CheckConstraint, Float, JSON, Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text, event
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


class HospitalVerificationStatus(str, Enum):
    """Private lifecycle for an institution's verification request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ModeratorAccessRequestStatus(str, Enum):
    """Private lifecycle for a verified user's moderator-access request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SafetyRuleKey(str, Enum):
    """The small, bounded configuration surface administrators may later edit."""

    MINIMUM_PUBLICATION_CONFIDENCE = "minimum_publication_confidence"
    MAXIMUM_PUBLICATION_FRAUD_RISK = "maximum_publication_fraud_risk"
    ROAD_ACCIDENT_EXPIRY_HOURS = "road_accident_expiry_hours"
    UNKNOWN_HOSPITAL_PATIENT_EXPIRY_HOURS = "unknown_hospital_patient_expiry_hours"


SAFETY_RULE_SPECS: dict[SafetyRuleKey, dict[str, int]] = {
    SafetyRuleKey.MINIMUM_PUBLICATION_CONFIDENCE: {"default": 80, "minimum": 50, "maximum": 100},
    SafetyRuleKey.MAXIMUM_PUBLICATION_FRAUD_RISK: {"default": 80, "minimum": 5, "maximum": 80},
    SafetyRuleKey.ROAD_ACCIDENT_EXPIRY_HOURS: {"default": 24, "minimum": 1, "maximum": 72},
    SafetyRuleKey.UNKNOWN_HOSPITAL_PATIENT_EXPIRY_HOURS: {"default": 72, "minimum": 1, "maximum": 72},
}


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
    created_share_links: Mapped[list["AlertShareLink"]] = relationship(
        back_populates="created_by",
        foreign_keys="AlertShareLink.created_by_id",
    )
    hospital_verification_requests: Mapped[list["HospitalVerificationRequest"]] = relationship(
        back_populates="submitted_by",
        foreign_keys="HospitalVerificationRequest.submitted_by_id",
    )
    reviewed_hospital_verification_requests: Mapped[list["HospitalVerificationRequest"]] = relationship(
        back_populates="reviewed_by",
        foreign_keys="HospitalVerificationRequest.reviewed_by_id",
    )
    moderator_access_requests: Mapped[list["ModeratorAccessRequest"]] = relationship(
        back_populates="submitted_by",
        foreign_keys="ModeratorAccessRequest.submitted_by_id",
    )
    reviewed_moderator_access_requests: Mapped[list["ModeratorAccessRequest"]] = relationship(
        back_populates="reviewed_by",
        foreign_keys="ModeratorAccessRequest.reviewed_by_id",
    )
    administration_audit_entries: Mapped[list["AdministrationAuditEntry"]] = relationship(
        back_populates="actor",
        foreign_keys="AdministrationAuditEntry.actor_id",
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
    road_accident_media_review: Mapped["RoadAccidentMediaReview | None"] = relationship(
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
    share_links: Mapped[list["AlertShareLink"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="AlertShareLink.created_at.desc()",
    )
    administration_audit_entries: Mapped[list["AdministrationAuditEntry"]] = relationship(
        back_populates="alert",
        foreign_keys="AdministrationAuditEntry.alert_id",
    )

    def __repr__(self) -> str:
        return f"<Alert {self.id} {self.alert_type.value} {self.status.value}>"


class AlertShareLink(db.Model):
    """Opaque, revocable external access to an alert's T49-safe representation."""

    __tablename__ = "alert_share_links"
    __table_args__ = (
        Index("ix_alert_share_links_alert_active", "alert_id", "revoked_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    alert: Mapped[Alert] = relationship(back_populates="share_links")
    created_by: Mapped[User] = relationship(back_populates="created_share_links", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f"<AlertShareLink alert_id={self.alert_id} expires_at={self.expires_at}>"


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


class RoadAccidentMediaReview(db.Model):
    """Auditable safety outcome for optional road-accident media.

    The review is private: it records only the stored media reference, a safe
    status, and a reporter-friendly explanation.  It never exposes the image
    or model reasoning in public alert content.
    """

    __tablename__ = "road_accident_media_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    media_reference: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    alert: Mapped[Alert] = relationship(back_populates="road_accident_media_review")

    def __repr__(self) -> str:
        return f"<RoadAccidentMediaReview alert_id={self.alert_id} status={self.status}>"


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


class HospitalVerificationRequest(db.Model):
    """Private request for a health institution to become a verified publisher.

    T41 stores only references to supporting documents, never the documents in
    public media storage. T43 will provide the administrator decision flow.
    """

    __tablename__ = "hospital_verification_requests"
    __table_args__ = (
        Index("ix_hospital_verification_requests_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    hospital_name: Mapped[str] = mapped_column(String(180), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    supporting_document_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[HospitalVerificationStatus] = mapped_column(
        SqlEnum(HospitalVerificationStatus, native_enum=False, length=32),
        nullable=False,
        default=HospitalVerificationStatus.PENDING,
        index=True,
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    submitted_by: Mapped[User] = relationship(
        back_populates="hospital_verification_requests", foreign_keys=[submitted_by_id]
    )
    reviewed_by: Mapped[User | None] = relationship(
        back_populates="reviewed_hospital_verification_requests", foreign_keys=[reviewed_by_id]
    )
    administration_audit_entries: Mapped[list["AdministrationAuditEntry"]] = relationship(
        back_populates="hospital_verification_request",
        foreign_keys="AdministrationAuditEntry.hospital_verification_request_id",
    )

    def submission_validation_errors(self) -> dict[str, str]:
        """Validate the private fields required before an institution applies."""
        errors: dict[str, str] = {}
        for field, label, minimum, maximum in (
            ("hospital_name", "Hospital name", 3, 180),
            ("country", "Country", 2, 80),
            ("region", "Region", 2, 120),
            ("contact_name", "Contact name", 2, 120),
            ("contact_phone", "Contact phone", 7, 32),
            ("supporting_document_reference", "Supporting-document reference", 3, 500),
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
                errors[field] = f"{label} is required and must be between {minimum} and {maximum} characters."
        return errors

    def decision_validation_errors(self) -> dict[str, str]:
        """Require an accountable reviewer and reason for any final decision."""
        errors = self.submission_validation_errors()
        if self.status in {HospitalVerificationStatus.APPROVED, HospitalVerificationStatus.REJECTED}:
            if self.reviewed_by_id is None:
                errors["reviewed_by_id"] = "A reviewer is required for a final verification decision."
            if self.reviewed_at is None:
                errors["reviewed_at"] = "A review timestamp is required for a final verification decision."
            if not self.decision_reason or not self.decision_reason.strip():
                errors["decision_reason"] = "A decision reason is required."
        return errors

    def __repr__(self) -> str:
        return f"<HospitalVerificationRequest {self.id} status={self.status.value}>"


class ModeratorAccessRequest(db.Model):
    """Private, auditable request for moderator access; never a public profile field."""

    __tablename__ = "moderator_access_requests"
    __table_args__ = (Index("ix_moderator_access_requests_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ModeratorAccessRequestStatus] = mapped_column(
        SqlEnum(ModeratorAccessRequestStatus, native_enum=False, length=32),
        nullable=False,
        default=ModeratorAccessRequestStatus.PENDING,
        index=True,
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    submitted_by: Mapped[User] = relationship(
        back_populates="moderator_access_requests", foreign_keys=[submitted_by_id]
    )
    reviewed_by: Mapped[User | None] = relationship(
        back_populates="reviewed_moderator_access_requests", foreign_keys=[reviewed_by_id]
    )

    def submission_validation_errors(self) -> dict[str, str]:
        """Require a concise, accountable reason before an access request is queued."""
        reason = self.reason.strip() if isinstance(self.reason, str) else ""
        if not 10 <= len(reason) <= 2000:
            return {"reason": "Explain the requested moderator access in 10 to 2000 characters."}
        return {}

    def decision_validation_errors(self) -> dict[str, str]:
        """Require the administrator and an explicit reason for a final decision."""
        errors = self.submission_validation_errors()
        if self.status in {ModeratorAccessRequestStatus.APPROVED, ModeratorAccessRequestStatus.REJECTED}:
            if self.reviewed_by_id is None:
                errors["reviewed_by_id"] = "An administrator reviewer is required."
            if self.reviewed_at is None:
                errors["reviewed_at"] = "A review timestamp is required."
            if not self.decision_reason or not self.decision_reason.strip():
                errors["decision_reason"] = "A decision reason is required."
        return errors

    def __repr__(self) -> str:
        return f"<ModeratorAccessRequest {self.id} status={self.status.value}>"


class SafetyRule(db.Model):
    """A bounded, future-facing administration setting with a safe default."""

    __tablename__ = "safety_rules"
    __table_args__ = (CheckConstraint("value >= 0 AND value <= 720", name="ck_safety_rules_value_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[SafetyRuleKey] = mapped_column(
        SqlEnum(SafetyRuleKey, native_enum=False, length=64), unique=True, nullable=False
    )
    value: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    @property
    def specification(self) -> dict[str, int]:
        return SAFETY_RULE_SPECS[self.key]

    def validation_errors(self) -> dict[str, str]:
        """Reject thresholds and expiry values outside their safety envelope."""
        errors: dict[str, str] = {}
        try:
            specification = SAFETY_RULE_SPECS[self.key]
        except (KeyError, TypeError):
            errors["key"] = "Safety rule key is not supported."
            return errors
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            errors["value"] = "Safety-rule value must be a whole number."
        elif not specification["minimum"] <= self.value <= specification["maximum"]:
            errors["value"] = (
                f"{self.key.value} must be between {specification['minimum']} and {specification['maximum']}."
            )
        return errors

    def __repr__(self) -> str:
        return f"<SafetyRule {self.key.value}={self.value}>"


class AdministrationAuditEntry(db.Model):
    """Immutable private audit metadata for administrator and moderator actions."""

    __tablename__ = "administration_audit_entries"
    __table_args__ = (
        Index("ix_administration_audit_actor_created", "actor_id", "created_at"),
        Index("ix_administration_audit_action_created", "action", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    prior_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    new_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    alert_id: Mapped[str | None] = mapped_column(ForeignKey("alerts.id", ondelete="SET NULL"), index=True)
    hospital_verification_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("hospital_verification_requests.id", ondelete="SET NULL"), index=True
    )
    moderator_access_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("moderator_access_requests.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    actor: Mapped[User] = relationship(back_populates="administration_audit_entries", foreign_keys=[actor_id])
    alert: Mapped[Alert | None] = relationship(back_populates="administration_audit_entries", foreign_keys=[alert_id])
    hospital_verification_request: Mapped[HospitalVerificationRequest | None] = relationship(
        back_populates="administration_audit_entries", foreign_keys=[hospital_verification_request_id]
    )
    moderator_access_request: Mapped[ModeratorAccessRequest | None] = relationship(
        foreign_keys=[moderator_access_request_id]
    )

    def validation_errors(self) -> dict[str, str]:
        """Ensure every immutable entry remains attributable and explainable."""
        errors: dict[str, str] = {}
        if self.actor_id is None:
            errors["actor_id"] = "An audit actor is required."
        if not self.action or not self.action.replace("_", "").replace("-", "").isalnum() or len(self.action) > 80:
            errors["action"] = "Audit action must be a short machine-readable value."
        if not self.reason or not self.reason.strip() or len(self.reason.strip()) > 2000:
            errors["reason"] = "Audit reason is required and must not exceed 2000 characters."
        return errors

    def __repr__(self) -> str:
        return f"<AdministrationAuditEntry {self.id} action={self.action}>"


@event.listens_for(AdministrationAuditEntry, "before_update")
def prevent_administration_audit_update(*_args) -> None:
    """Defend audit entries against ORM mutation after they are written."""
    raise ValueError("Administration audit entries are immutable.")


@event.listens_for(AdministrationAuditEntry, "before_delete")
def prevent_administration_audit_delete(*_args) -> None:
    """Defend audit entries against ORM deletion after they are written."""
    raise ValueError("Administration audit entries are immutable.")


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
    administrative_request_type: Mapped[str | None] = mapped_column(String(48), index=True)
    administrative_request_id: Mapped[str | None] = mapped_column(String(36), index=True)
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
    "AlertShareLink",
    "AlertStatus",
    "AlertType",
    "AIReview",
    "AdministrationAuditEntry",
    "HospitalVerificationRequest",
    "HospitalVerificationStatus",
    "MissingPersonDetails",
    "MissingPersonSex",
    "ModeratorAccessRequest",
    "ModeratorAccessRequestStatus",
    "Notification",
    "ReportAction",
    "RoadAccidentDetails",
    "RoadAccidentMediaReview",
    "SAFETY_RULE_SPECS",
    "SafetyRule",
    "SafetyRuleKey",
    "SuspectedAbductionDetails",
    "User",
    "UserRole",
    "db",
]
