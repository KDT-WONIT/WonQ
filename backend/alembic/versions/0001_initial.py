"""Create assets and asynchronous jobs."""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("department", sa.String(64), nullable=False),
        sa.Column("location", sa.String(128), nullable=False),
        sa.Column("qr_token", sa.Uuid(), nullable=False, unique=True),
    )
    op.create_index("ix_assets_department", "assets", ["department"])
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("department", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jobs_claim", "jobs", ["kind", "status", "created_at"])
    op.create_index("ix_jobs_publish", "jobs", ["status", "published_at", "created_at"])


def downgrade():
    op.drop_table("jobs")
    op.drop_table("assets")
