"""Add explicit public-media authorisation for safe identification photos.

Revision ID: f70b8c2d3e40
Revises: f62a7b3c9d21
Create Date: 2026-07-21 13:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f70b8c2d3e40"
down_revision = "f62a7b3c9d21"
branch_labels = None
depends_on = None


def upgrade():
    # Existing uploads remain private until the reporting user explicitly opts in.
    op.add_column(
        "missing_person_details",
        sa.Column("public_media_authorized", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "suspected_abduction_details",
        sa.Column("public_media_authorized", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("suspected_abduction_details", "public_media_authorized")
    op.drop_column("missing_person_details", "public_media_authorized")
