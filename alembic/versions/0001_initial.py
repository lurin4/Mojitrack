"""Initial accounts, library, logs, sessions and import receipts."""
import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(40), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("daily_goal", sa.Integer(), nullable=False),
        sa.Column("weekly_goal", sa.Integer(), nullable=False),
        sa.Column("monthly_goal", sa.Integer(), nullable=False),
        sa.Column("public_profile", sa.Boolean(), nullable=False))
    op.create_table("sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires", sa.Integer(), nullable=False))
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_table("api_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True))
    op.create_table("media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("jiten_id", sa.Integer(), nullable=True),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("total_chars", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.Float(), nullable=True),
        sa.Column("unique_words", sa.Integer(), nullable=True),
        sa.Column("unique_kanji", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "jiten_id"),
        sa.CheckConstraint("status IN ('reading', 'finished', 'dropped')"),
        sa.CheckConstraint("total_chars IS NULL OR total_chars > 0"))
    op.create_index("ix_media_user_id", "media", ["user_id"])
    op.create_table("logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("media_id", sa.Integer(), sa.ForeignKey("media.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("chars", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.CheckConstraint("chars > 0"),
        sa.CheckConstraint("minutes IS NULL OR minutes > 0"))
    op.create_index("ix_logs_user_date", "logs", ["user_id", "date"])
    op.create_table("imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.UniqueConstraint("user_id", "digest"))


def downgrade():
    for table in ("imports", "logs", "media", "api_tokens", "sessions", "users"):
        op.drop_table(table)
