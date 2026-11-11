"""Add required course level with a data backfill."""
from alembic import op
import sqlalchemy as sa
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("courses", sa.Column("level", sa.Text(), nullable=True))
    op.execute("UPDATE courses SET level = CASE WHEN is_elective THEN 'beginner' ELSE 'intermediate' END")
    op.alter_column("courses", "level", nullable=False)

def downgrade():
    op.drop_column("courses", "level")
