"""Add road-accident media safety reviews.

Revision ID: b72c3d5e8a42
Revises: a81d2e4f7b31
Create Date: 2026-07-20 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b72c3d5e8a42"
down_revision = "a81d2e4f7b31"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "road_accident_media_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("media_reference", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
    )


def downgrade():
    op.drop_table("road_accident_media_reviews")
