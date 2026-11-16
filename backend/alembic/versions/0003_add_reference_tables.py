"""Add the reference tables and nullable links to the existing ledgers."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

REFERENCES = {
    "assets": {
        "item_id": "items",
        "department_id": "departments",
        "location_id": "locations",
        "holder_id": "user_accounts",
        "intake_line_id": "intake_lines",
    },
    "audit_rounds": {"department_id": "departments", "location_id": "locations"},
    "intake_lines": {"item_id": "items", "location_id": "locations"},
    "intakes": {"supplier_id": "vendors", "department_id": "departments"},
    "stock": {"item_id": "items", "department_id": "departments", "location_id": "locations"},
}


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(80)),
        sa.Column("tracking", sa.String(16)),
        sa.Column("base_unit", sa.String(32)),
        sa.Column("attributes", postgresql.JSONB(none_as_null=True)),
    )
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("locations.id")),
    )
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])
    op.create_table(
        "vendors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
    )
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("departments.id")),
        sa.Column("default_location_id", sa.Uuid(), sa.ForeignKey("locations.id")),
    )
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("auth_subject", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(128)),
        sa.Column("department_id", sa.Uuid(), sa.ForeignKey("departments.id")),
        sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendors.id")),
    )
    op.create_table(
        "announcements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("user_accounts.id")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for table, links in REFERENCES.items():
        for column, target in links.items():
            op.add_column(table, sa.Column(column, sa.Uuid(), nullable=True))
            op.create_foreign_key(f"fk_{table}_{column}", table, target, [column], ["id"])
    op.create_index("ix_assets_item_id", "assets", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_assets_item_id", table_name="assets")
    for table, links in REFERENCES.items():
        for column in links:
            op.drop_constraint(f"fk_{table}_{column}", table, type_="foreignkey")
            op.drop_column(table, column)
    for table in ("announcements", "user_accounts", "departments", "vendors", "locations", "items"):
        op.drop_table(table)

