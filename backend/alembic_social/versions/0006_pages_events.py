"""Pages + événements — Couche 6b.

Revision ID: 0006_pages_events
Revises: 0005_groups_stories
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0006_pages_events"
down_revision = "0005_groups_stories"
branch_labels = None
depends_on = None

_T = ["social_pages", "social_page_roles", "social_page_followers",
      "social_events", "social_event_rsvps"]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in _T])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in reversed(_T)])
