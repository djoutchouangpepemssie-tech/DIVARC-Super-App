"""Ajoute la table des bookmarks (Couche 3).

Revision ID: 0002_bookmarks
Revises: 0001_initial_social
"""
from alembic import op

from app.social.adapters.persistence import models  # noqa: F401
from app.social.adapters.persistence.db import Base

revision = "0002_bookmarks"
down_revision = "0001_initial_social"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables["social_bookmarks"]])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables["social_bookmarks"]])
