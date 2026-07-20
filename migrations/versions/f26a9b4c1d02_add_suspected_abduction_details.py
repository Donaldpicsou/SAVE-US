"""Add dedicated suspected-abduction details

Revision ID: f26a9b4c1d02
Revises: e24d7b8c9a10
Create Date: 2026-07-20 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f26a9b4c1d02"
down_revision = "e24d7b8c9a10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "suspected_abduction_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("photo_path", sa.String(length=500), nullable=True),
        sa.Column("abduction_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("circumstances", sa.Text(), nullable=True),
        sa.Column("private_contact", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
    )


def downgrade():
    op.drop_table("suspected_abduction_details")
