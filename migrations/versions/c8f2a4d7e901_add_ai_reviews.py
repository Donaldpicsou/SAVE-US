"""Add persisted AI reviews

Revision ID: c8f2a4d7e901
Revises: b7d3e10f4c20
Create Date: 2026-07-20 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f2a4d7e901"
down_revision = "b7d3e10f4c20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("public_summary", sa.Text(), nullable=False),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("missing_fields", sa.JSON(), nullable=False),
        sa.Column("duplicate_candidates", sa.JSON(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("fraud_risk_score", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("fallback_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
    )


def downgrade():
    op.drop_table("ai_reviews")
