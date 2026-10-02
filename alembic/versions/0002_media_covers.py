"""Store Jiten cover URLs without changing reading history."""
import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("media", sa.Column("cover_url", sa.String(), nullable=True))


def downgrade():
    op.drop_column("media", "cover_url")
