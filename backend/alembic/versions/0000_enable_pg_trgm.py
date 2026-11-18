"""Enable the pg_trgm extension (needed by the listing search index).

Revision ID: 0000_pg_trgm
Revises:
Create Date: 2026-11-18
"""

from alembic import op

revision = "0000_pg_trgm"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    # Leave the extension in place; other things may use it.
    pass
