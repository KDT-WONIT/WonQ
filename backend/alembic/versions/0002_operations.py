"""Add intake, stock, audit and notification records."""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('audit_rounds',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('department', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('assigned_to', sa.String(length=128), nullable=False),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_rounds_department'), 'audit_rounds', ['department'], unique=False)
    op.create_table('intakes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('vendor_id', sa.String(length=64), nullable=False),
        sa.Column('owner_id', sa.String(length=128), nullable=False),
        sa.Column('document_number', sa.String(length=80), nullable=False),
        sa.Column('department', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('review_note', sa.String(length=500), nullable=True),
        sa.Column('reviewed_by', sa.String(length=128), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signed_by', sa.String(length=128), nullable=True),
        sa.Column('signer_name', sa.String(length=80), nullable=True),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_by', sa.String(length=128), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vendor_id', 'document_number')
    )
    op.create_index(op.f('ix_intakes_department'), 'intakes', ['department'], unique=False)
    op.create_table('movements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('stable_key', sa.String(length=120), nullable=False),
        sa.Column('department', sa.String(length=64), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('target', sa.String(length=128), nullable=False),
        sa.Column('actor', sa.String(length=128), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stable_key')
    )
    op.create_index(op.f('ix_movements_department'), 'movements', ['department'], unique=False)
    op.create_table('notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('audience', sa.String(length=20), nullable=False),
        sa.Column('recipient', sa.String(length=128), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('reference_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_recipient'), 'notifications', ['recipient'], unique=False)
    op.create_table('stock',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('department', sa.String(length=64), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('location', sa.String(length=128), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('safety_stock', sa.Integer(), nullable=False),
        sa.CheckConstraint('quantity >= 0', name='ck_stock_nonnegative'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department', 'item_code', 'location')
    )
    op.create_index(op.f('ix_stock_department'), 'stock', ['department'], unique=False)
    op.create_table('audit_targets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('round_id', sa.Uuid(), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=False),
        sa.Column('expected_location', sa.String(length=128), nullable=False),
        sa.Column('expected_quantity', sa.Integer(), nullable=False),
        sa.Column('observed_location', sa.String(length=128), nullable=True),
        sa.Column('observed_quantity', sa.Integer(), nullable=True),
        sa.Column('observed_by', sa.String(length=128), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['round_id'], ['audit_rounds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('round_id', 'target_id')
    )
    op.create_index(op.f('ix_audit_targets_round_id'), 'audit_targets', ['round_id'], unique=False)
    op.create_table('intake_lines',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('intake_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('tracking', sa.String(length=16), nullable=False),
        sa.Column('submitted_quantity', sa.Integer(), nullable=False),
        sa.Column('approved_quantity', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=128), nullable=False),
        sa.Column('labels', sa.JSON(), nullable=False),
        sa.Column('received_quantity', sa.Integer(), nullable=True),
        sa.Column('accepted_quantity', sa.Integer(), nullable=True),
        sa.Column('serials', sa.JSON(), nullable=False),
        sa.Column('variance_note', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['intake_id'], ['intakes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_intake_lines_intake_id'), 'intake_lines', ['intake_id'], unique=False)
    op.create_table('notification_reads',
        sa.Column('notification_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('notification_id', 'user_id')
    )
    op.add_column('assets', sa.Column('item_code', sa.String(length=64), nullable=True))
    op.add_column('assets', sa.Column('serial', sa.String(length=128), nullable=True))
    op.add_column('assets', sa.Column('status', sa.String(length=20), server_default='stored', nullable=False))
    op.create_unique_constraint('uq_assets_item_serial', 'assets', ['item_code', 'serial'])


def downgrade() -> None:
    op.drop_constraint('uq_assets_item_serial', 'assets', type_='unique')
    op.drop_column('assets', 'status')
    op.drop_column('assets', 'serial')
    op.drop_column('assets', 'item_code')
    op.drop_table('notification_reads')
    op.drop_index(op.f('ix_intake_lines_intake_id'), table_name='intake_lines')
    op.drop_table('intake_lines')
    op.drop_index(op.f('ix_audit_targets_round_id'), table_name='audit_targets')
    op.drop_table('audit_targets')
    op.drop_index(op.f('ix_stock_department'), table_name='stock')
    op.drop_table('stock')
    op.drop_index(op.f('ix_notifications_recipient'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_movements_department'), table_name='movements')
    op.drop_table('movements')
    op.drop_index(op.f('ix_intakes_department'), table_name='intakes')
    op.drop_table('intakes')
    op.drop_index(op.f('ix_audit_rounds_department'), table_name='audit_rounds')
    op.drop_table('audit_rounds')
