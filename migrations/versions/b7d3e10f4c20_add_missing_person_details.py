"""Add missing-person reporting details

Revision ID: b7d3e10f4c20
Revises: a43ca6faabcd
Create Date: 2026-07-19 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b7d3e10f4c20"
down_revision = "a43ca6faabcd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "missing_person_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("photo_path", sa.String(length=500), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_location", sa.String(length=255), nullable=True),
        sa.Column("clothing_description", sa.Text(), nullable=True),
        sa.Column("private_family_contact", sa.String(length=64), nullable=True),
        sa.Column("circumstances", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("age IS NULL OR (age >= 0 AND age <= 125)", name="ck_missing_person_age_range"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
    )


def downgrade():
    op.drop_table("missing_person_details")
