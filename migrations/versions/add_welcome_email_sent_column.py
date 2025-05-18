"""
Add welcome_email_sent column to user table

Revision ID: add_welcome_email_sent_column
Revises: 202406_last_seen_addition
Create Date: 2025-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_welcome_email_sent_column'
down_revision = '202406_last_seen_addition'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('welcome_email_sent', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE user SET welcome_email_sent = 0")

def downgrade():
    op.drop_column('user', 'welcome_email_sent') 