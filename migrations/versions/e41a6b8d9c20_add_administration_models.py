"""Add hospital-verification, safety-rule, and immutable administration-audit models.

Revision ID: e41a6b8d9c20
Revises: c31e5f9a2b70
Create Date: 2026-07-21 05:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


revision = "e41a6b8d9c20"
down_revision = "c31e5f9a2b70"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hospital_verification_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submitted_by_id", sa.Integer(), nullable=False),
        sa.Column("hospital_name", sa.String(length=180), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=False),
        sa.Column("contact_name", sa.String(length=120), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("supporting_document_reference", sa.String(length=500), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="hospitalverificationstatus", native_enum=False, length=32), nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hospital_verification_requests_submitted_by_id", "hospital_verification_requests", ["submitted_by_id"])
    op.create_index("ix_hospital_verification_requests_reviewed_by_id", "hospital_verification_requests", ["reviewed_by_id"])
    op.create_index("ix_hospital_verification_requests_status", "hospital_verification_requests", ["status"])
    op.create_index("ix_hospital_verification_requests_status_created", "hospital_verification_requests", ["status", "created_at"])

    op.create_table(
        "safety_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Enum("MINIMUM_PUBLICATION_CONFIDENCE", "MAXIMUM_PUBLICATION_FRAUD_RISK", "ROAD_ACCIDENT_EXPIRY_HOURS", "UNKNOWN_HOSPITAL_PATIENT_EXPIRY_HOURS", name="safetyrulekey", native_enum=False, length=64), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("value >= 0 AND value <= 720", name="ck_safety_rules_value_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    safety_rules = sa.table(
        "safety_rules",
        sa.column("key", sa.String),
        sa.column("value", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        safety_rules,
        [
            {"key": "MINIMUM_PUBLICATION_CONFIDENCE", "value": 80, "created_at": now, "updated_at": now},
            {"key": "MAXIMUM_PUBLICATION_FRAUD_RISK", "value": 80, "created_at": now, "updated_at": now},
            {"key": "ROAD_ACCIDENT_EXPIRY_HOURS", "value": 24, "created_at": now, "updated_at": now},
            {"key": "UNKNOWN_HOSPITAL_PATIENT_EXPIRY_HOURS", "value": 72, "created_at": now, "updated_at": now},
        ],
    )

    op.create_table(
        "administration_audit_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("prior_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("alert_id", sa.String(length=36), nullable=True),
        sa.Column("hospital_verification_request_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hospital_verification_request_id"], ["hospital_verification_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_administration_audit_entries_actor_id", "administration_audit_entries", ["actor_id"])
    op.create_index("ix_administration_audit_entries_target_user_id", "administration_audit_entries", ["target_user_id"])
    op.create_index("ix_administration_audit_entries_alert_id", "administration_audit_entries", ["alert_id"])
    op.create_index("ix_administration_audit_entries_hospital_verification_request_id", "administration_audit_entries", ["hospital_verification_request_id"])
    op.create_index("ix_administration_audit_actor_created", "administration_audit_entries", ["actor_id", "created_at"])
    op.create_index("ix_administration_audit_action_created", "administration_audit_entries", ["action", "created_at"])

    # SQLite-level guards complement ORM hooks, including direct SQL attempts.
    if op.get_bind().dialect.name == "sqlite":
        op.execute("""
            CREATE TRIGGER prevent_administration_audit_update
            BEFORE UPDATE ON administration_audit_entries
            BEGIN
                SELECT RAISE(ABORT, 'Administration audit entries are immutable.');
            END;
        """)
        op.execute("""
            CREATE TRIGGER prevent_administration_audit_delete
            BEFORE DELETE ON administration_audit_entries
            BEGIN
                SELECT RAISE(ABORT, 'Administration audit entries are immutable.');
            END;
        """)


def downgrade():
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS prevent_administration_audit_delete")
        op.execute("DROP TRIGGER IF EXISTS prevent_administration_audit_update")
    op.drop_index("ix_administration_audit_action_created", table_name="administration_audit_entries")
    op.drop_index("ix_administration_audit_actor_created", table_name="administration_audit_entries")
    op.drop_index("ix_administration_audit_entries_hospital_verification_request_id", table_name="administration_audit_entries")
    op.drop_index("ix_administration_audit_entries_alert_id", table_name="administration_audit_entries")
    op.drop_index("ix_administration_audit_entries_target_user_id", table_name="administration_audit_entries")
    op.drop_index("ix_administration_audit_entries_actor_id", table_name="administration_audit_entries")
    op.drop_table("administration_audit_entries")
    op.drop_table("safety_rules")
    op.drop_index("ix_hospital_verification_requests_status_created", table_name="hospital_verification_requests")
    op.drop_index("ix_hospital_verification_requests_status", table_name="hospital_verification_requests")
    op.drop_index("ix_hospital_verification_requests_reviewed_by_id", table_name="hospital_verification_requests")
    op.drop_index("ix_hospital_verification_requests_submitted_by_id", table_name="hospital_verification_requests")
    op.drop_table("hospital_verification_requests")
