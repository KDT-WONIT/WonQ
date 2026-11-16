"""Add planned workflows"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: str | Sequence[str] | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'forecast_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=True),
        sa.Column('item_id', sa.Uuid(), nullable=False),
        sa.Column('location_id', sa.Uuid(), nullable=False),
        sa.Column('target', sa.String(length=32), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('calculation', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_forecast_results_item_id'), 'forecast_results', ['item_id'], unique=False)
    op.create_table(
        'permission_requests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('requested_by', sa.Uuid(), nullable=False),
        sa.Column('role_code', sa.String(length=32), nullable=False),
        sa.Column('scope_department_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('decided_by', sa.Uuid(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['decided_by'], ['user_accounts.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['user_accounts.id'], ),
        sa.ForeignKeyConstraint(['scope_department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user_accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_permission_requests_user_id'), 'permission_requests', ['user_id'], unique=False)
    op.create_table(
        'reports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('department_id', sa.Uuid(), nullable=True),
        sa.Column('audit_round_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['audit_round_id'], ['audit_rounds.id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'audit_followups',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('movement_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['movement_id'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['target_id'], ['audit_targets.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_followups_target_id'), 'audit_followups', ['target_id'], unique=False)
    op.create_table(
        'report_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('report_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=True),
        sa.Column('job_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('criteria', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['user_accounts.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_id', 'version'),
    )
    op.create_table(
        'asset_requests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('asset_id', sa.Uuid(), nullable=False),
        sa.Column('requested_by', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('movement_id', sa.Uuid(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['movement_id'], ['movements.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['user_accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_asset_requests_asset_id'), 'asset_requests', ['asset_id'], unique=False)
    op.create_table(
        'equipment_components',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('equipment_id', sa.Uuid(), nullable=False),
        sa.Column('component_asset_id', sa.Uuid(), nullable=True),
        sa.Column('component_item_id', sa.Uuid(), nullable=True),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('(component_asset_id IS NULL) <> (component_item_id IS NULL)', name='ck_equipment_components_has_one_component'),
        sa.ForeignKeyConstraint(['component_asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['component_item_id'], ['items.id'], ),
        sa.ForeignKeyConstraint(['equipment_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_equipment_components_equipment_id'), 'equipment_components', ['equipment_id'], unique=False)
    op.create_table(
        'maintenance_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('asset_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_to', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('scheduled_for', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['user_accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_maintenance_records_asset_id'), 'maintenance_records', ['asset_id'], unique=False)
    op.create_table(
        'qr_issues',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('intake_line_id', sa.Uuid(), nullable=True),
        sa.Column('asset_id', sa.Uuid(), nullable=True),
        sa.Column('stock_id', sa.Uuid(), nullable=True),
        sa.Column('previous_token', sa.Uuid(), nullable=True),
        sa.Column('token', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=24), nullable=False),
        sa.Column('issued_by', sa.Uuid(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('intake_line_id IS NOT NULL OR asset_id IS NOT NULL OR stock_id IS NOT NULL', name='ck_qr_issues_has_target'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['intake_line_id'], ['intake_lines.id'], ),
        sa.ForeignKeyConstraint(['issued_by'], ['user_accounts.id'], ),
        sa.ForeignKeyConstraint(['stock_id'], ['stock.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_qr_issues_asset_id'), 'qr_issues', ['asset_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_qr_issues_asset_id'), table_name='qr_issues')
    op.drop_table('qr_issues')
    op.drop_index(op.f('ix_maintenance_records_asset_id'), table_name='maintenance_records')
    op.drop_table('maintenance_records')
    op.drop_index(op.f('ix_equipment_components_equipment_id'), table_name='equipment_components')
    op.drop_table('equipment_components')
    op.drop_index(op.f('ix_asset_requests_asset_id'), table_name='asset_requests')
    op.drop_table('asset_requests')
    op.drop_table('report_versions')
    op.drop_index(op.f('ix_audit_followups_target_id'), table_name='audit_followups')
    op.drop_table('audit_followups')
    op.drop_table('reports')
    op.drop_index(op.f('ix_permission_requests_user_id'), table_name='permission_requests')
    op.drop_table('permission_requests')
    op.drop_index(op.f('ix_forecast_results_item_id'), table_name='forecast_results')
    op.drop_table('forecast_results')
