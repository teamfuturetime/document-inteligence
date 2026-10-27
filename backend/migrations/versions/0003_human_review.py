"""separate human OCR and classification review from machine output

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("ocr_text_corrected", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("ocr_corrected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("extractions", sa.Column("ai_document_type", sa.String(50), nullable=True))
    op.add_column("extractions", sa.Column("reviewed_document_type", sa.String(50), nullable=True))
    op.execute("UPDATE extractions SET ai_document_type = document_type WHERE ai_document_type IS NULL")


def downgrade() -> None:
    op.drop_column("extractions", "reviewed_document_type")
    op.drop_column("extractions", "ai_document_type")
    op.drop_column("documents", "ocr_corrected_at")
    op.drop_column("documents", "ocr_text_corrected")
