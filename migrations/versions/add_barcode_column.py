"""add barcode column

Revision ID: add_barcode_column
Revises: 
Create Date: 2025-04-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_barcode_column'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add barcode column to product table
    op.add_column('product', sa.Column('barcode', sa.String(50), unique=True, nullable=True))

def downgrade():
    # Remove barcode column from product table
    op.drop_column('product', 'barcode') 