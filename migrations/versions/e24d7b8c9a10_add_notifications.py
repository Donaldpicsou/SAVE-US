"""Add persistent in-app notifications

Revision ID: e24d7b8c9a10
Revises: d19a6c3e5f02
Create Date: 2026-07-20 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e24d7b8c9a10"
down_revision = "d19a6c3e5f02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("public_location", sa.String(length=180), nullable=True),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("email_delivery_status", sa.String(length=32), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_recipient_created", "notifications", ["recipient_id", "created_at"])
    op.create_index("ix_notifications_recipient_read", "notifications", ["recipient_id", "is_read"])
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])
    op.create_index("ix_notifications_alert_id", "notifications", ["alert_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade():
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_alert_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_read", table_name="notifications")
    op.drop_index("ix_notifications_recipient_created", table_name="notifications")
    op.drop_table("notifications")
