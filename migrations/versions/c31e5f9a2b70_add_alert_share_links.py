"""Add opaque, revocable alert share links.

Revision ID: c31e5f9a2b70
Revises: b72c3d5e8a42
Create Date: 2026-07-21 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c31e5f9a2b70"
down_revision = "b72c3d5e8a42"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alert_share_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=96), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_alert_share_links_alert_id", "alert_share_links", ["alert_id"], unique=False)
    op.create_index("ix_alert_share_links_created_by_id", "alert_share_links", ["created_by_id"], unique=False)
    op.create_index("ix_alert_share_links_expires_at", "alert_share_links", ["expires_at"], unique=False)
    op.create_index("ix_alert_share_links_revoked_at", "alert_share_links", ["revoked_at"], unique=False)
    op.create_index("ix_alert_share_links_alert_active", "alert_share_links", ["alert_id", "revoked_at", "expires_at"], unique=False)
    op.create_index("ix_alert_share_links_token", "alert_share_links", ["token"], unique=True)


def downgrade():
    op.drop_index("ix_alert_share_links_token", table_name="alert_share_links")
    op.drop_index("ix_alert_share_links_alert_active", table_name="alert_share_links")
    op.drop_index("ix_alert_share_links_revoked_at", table_name="alert_share_links")
    op.drop_index("ix_alert_share_links_expires_at", table_name="alert_share_links")
    op.drop_index("ix_alert_share_links_created_by_id", table_name="alert_share_links")
    op.drop_index("ix_alert_share_links_alert_id", table_name="alert_share_links")
    op.drop_table("alert_share_links")
