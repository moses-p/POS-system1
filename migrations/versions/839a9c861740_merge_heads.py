"""merge heads

Revision ID: 839a9c861740
Revises: 274e92ebc845, add_welcome_email_sent_column
Create Date: 2025-05-17 09:23:40.432277

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '839a9c861740'
down_revision = ('274e92ebc845', 'add_welcome_email_sent_column')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
