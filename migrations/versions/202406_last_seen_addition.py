"""
Add last_seen column to user table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from datetime import datetime

# Alembic identifiers
revision = '202406_last_seen_addition'
down_revision = 'ded0ad5a94c6'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('user')]
    if 'last_seen' not in columns:
        op.add_column('user', sa.Column('last_seen', sa.DateTime(), nullable=True, server_default=sa.func.now()))
        # Optionally, set all existing users' last_seen to now
        conn.execute("UPDATE user SET last_seen = ?", (datetime.utcnow(),))

def downgrade():
    op.drop_column('user', 'last_seen') 