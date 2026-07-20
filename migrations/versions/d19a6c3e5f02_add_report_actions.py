"""Add reporter closure audit actions

Revision ID: d19a6c3e5f02
Revises: c8f2a4d7e901
Create Date: 2026-07-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d19a6c3e5f02"
down_revision = "c8f2a4d7e901"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "report_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_actions_alert_created", "report_actions", ["alert_id", "created_at"])
    op.create_index("ix_report_actions_actor_id", "report_actions", ["actor_id"])
    op.create_index("ix_report_actions_alert_id", "report_actions", ["alert_id"])


def downgrade():
    op.drop_index("ix_report_actions_alert_id", table_name="report_actions")
    op.drop_index("ix_report_actions_actor_id", table_name="report_actions")
    op.drop_index("ix_report_actions_alert_created", table_name="report_actions")
    op.drop_table("report_actions")
