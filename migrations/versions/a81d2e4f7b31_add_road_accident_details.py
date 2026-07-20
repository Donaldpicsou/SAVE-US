"""Add dedicated road-accident details.

Revision ID: a81d2e4f7b31
Revises: f26a9b4c1d02
Create Date: 2026-07-20 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a81d2e4f7b31"
down_revision = "f26a9b4c1d02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "road_accident_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manual_location", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("affected_region", sa.String(length=120), nullable=True),
        sa.Column("victim_count", sa.Integer(), nullable=True),
        sa.Column("immediate_needs", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("media_references", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("victim_count IS NULL OR victim_count >= 0", name="ck_road_accident_victim_count_nonnegative"),
        sa.CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_road_accident_latitude_range"),
        sa.CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_road_accident_longitude_range"),
        sa.CheckConstraint("(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)", name="ck_road_accident_coordinate_pair"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
    )


def downgrade():
    op.drop_table("road_accident_details")
