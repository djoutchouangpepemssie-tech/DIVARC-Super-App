"""Modération + transparence (signalements, journal) — Couche 9.

Revision ID: 0007_moderation
Revises: 0006_pages_events
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0007_moderation"
down_revision = "0006_pages_events"
branch_labels = None
depends_on = None

_T = ["social_reports", "social_moderation_actions"]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in _T])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in reversed(_T)])
