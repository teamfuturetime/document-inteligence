"""authentication sessions and document ownership

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("username", sa.String(80), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("email"), sa.UniqueConstraint("username"))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("user_sessions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("user_id", sa.String(36), nullable=False), sa.Column("csrf_token", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.String(36), nullable=True))
        batch_op.create_index("ix_documents_owner_id", ["owner_id"])
        batch_op.create_foreign_key("fk_documents_owner", "users", ["owner_id"], ["id"], ondelete="CASCADE")
    op.add_column("extractions", sa.Column("classification_metadata", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("extractions", "classification_metadata")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("fk_documents_owner", type_="foreignkey")
        batch_op.drop_index("ix_documents_owner_id")
        batch_op.drop_column("owner_id")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
