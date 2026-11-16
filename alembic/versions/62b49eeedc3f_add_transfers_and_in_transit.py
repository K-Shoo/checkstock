"""add transfers and in_transit

Revision ID: 62b49eeedc3f
Revises: 468363f83c36
Create Date: 2026-11-16 13:03:05.758762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '62b49eeedc3f'
down_revision: Union[str, None] = '468363f83c36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'in_transit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('from_warehouse_id', sa.Integer(), nullable=False),
        sa.Column('to_warehouse_id', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.String(length=32),
            server_default='IN_TRANSIT',
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['operation_id'], ['operations.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['from_warehouse_id'], ['warehouses.id']),
        sa.ForeignKeyConstraint(['to_warehouse_id'], ['warehouses.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('from_warehouse_id', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('to_warehouse_id', sa.Integer(), nullable=True)
        )
        batch_op.alter_column(
            'warehouse_id',
            existing_type=sa.INTEGER(),
            nullable=True,
        )
        batch_op.create_foreign_key(
            'fk_operations_from_warehouse_id',
            'warehouses',
            ['from_warehouse_id'],
            ['id'],
        )
        batch_op.create_foreign_key(
            'fk_operations_to_warehouse_id',
            'warehouses',
            ['to_warehouse_id'],
            ['id'],
        )


def downgrade() -> None:
    with op.batch_alter_table('operations', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_operations_to_warehouse_id',
            type_='foreignkey',
        )
        batch_op.drop_constraint(
            'fk_operations_from_warehouse_id',
            type_='foreignkey',
        )
        batch_op.drop_column('to_warehouse_id')
        batch_op.drop_column('from_warehouse_id')
        batch_op.alter_column(
            'warehouse_id',
            existing_type=sa.INTEGER(),
            nullable=False,
        )

    op.drop_table('in_transit')
