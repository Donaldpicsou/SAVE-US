"""Core SQLAlchemy entities for SAVE-US.

Detailed report fields, AI reviews, media, notifications, and reporter actions
are added in subsequent roadmap tasks. These models establish the shared
identity, targeting, and alert lifecycle foundation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text
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

    def __repr__(self) -> str:
        return f"<Alert {self.id} {self.alert_type.value} {self.status.value}>"


__all__ = [
    "Alert",
    "AlertPreference",
    "AlertStatus",
    "AlertType",
    "User",
    "UserRole",
    "db",
]
