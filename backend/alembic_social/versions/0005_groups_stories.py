"""Groupes + stories — Couche 6a.

Revision ID: 0005_groups_stories
Revises: 0004_hidden
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0005_groups_stories"
down_revision = "0004_hidden"
branch_labels = None
depends_on = None

_T = ["social_groups", "social_group_members", "social_stories", "social_story_views"]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in _T])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[t] for t in reversed(_T)])
