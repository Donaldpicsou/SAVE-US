"""Add private moderator-access requests and administrative notification references.

Revision ID: f62a7b3c9d21
Revises: e41a6b8d9c20
Create Date: 2026-07-21 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f62a7b3c9d21"
down_revision = "e41a6b8d9c20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "moderator_access_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submitted_by_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="moderatoraccessrequeststatus", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderator_access_requests_submitted_by_id", "moderator_access_requests", ["submitted_by_id"])
    op.create_index("ix_moderator_access_requests_reviewed_by_id", "moderator_access_requests", ["reviewed_by_id"])
    op.create_index("ix_moderator_access_requests_status", "moderator_access_requests", ["status"])
    op.create_index("ix_moderator_access_requests_status_created", "moderator_access_requests", ["status", "created_at"])

    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("administrative_request_type", sa.String(length=48), nullable=True))
        batch.add_column(sa.Column("administrative_request_id", sa.String(length=36), nullable=True))
        batch.create_index("ix_notifications_administrative_request_type", ["administrative_request_type"])
        batch.create_index("ix_notifications_administrative_request_id", ["administrative_request_id"])

    with op.batch_alter_table("administration_audit_entries") as batch:
        batch.add_column(sa.Column("moderator_access_request_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_administration_audit_entries_moderator_access_request_id",
            "moderator_access_requests",
            ["moderator_access_request_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_administration_audit_entries_moderator_access_request_id",
            ["moderator_access_request_id"],
        )


def downgrade():
    with op.batch_alter_table("administration_audit_entries") as batch:
        batch.drop_index("ix_administration_audit_entries_moderator_access_request_id")
        batch.drop_constraint("fk_administration_audit_entries_moderator_access_request_id", type_="foreignkey")
        batch.drop_column("moderator_access_request_id")

    with op.batch_alter_table("notifications") as batch:
        batch.drop_index("ix_notifications_administrative_request_id")
        batch.drop_index("ix_notifications_administrative_request_type")
        batch.drop_column("administrative_request_id")
        batch.drop_column("administrative_request_type")

    op.drop_index("ix_moderator_access_requests_status_created", table_name="moderator_access_requests")
    op.drop_index("ix_moderator_access_requests_status", table_name="moderator_access_requests")
    op.drop_index("ix_moderator_access_requests_reviewed_by_id", table_name="moderator_access_requests")
    op.drop_index("ix_moderator_access_requests_submitted_by_id", table_name="moderator_access_requests")
    op.drop_table("moderator_access_requests")
