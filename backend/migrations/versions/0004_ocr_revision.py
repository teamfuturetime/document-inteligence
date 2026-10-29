"""add optimistic concurrency revision for OCR corrections

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A persistent server default also covers existing rows and direct inserts.
    op.add_column("documents", sa.Column("ocr_revision", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("documents", "ocr_revision")
