from app import db

def upgrade():
    # Add barcode column to Product table
    db.engine.execute('ALTER TABLE product ADD COLUMN barcode VARCHAR(50) UNIQUE')
 
def downgrade():
    # Remove barcode column from Product table
    db.engine.execute('ALTER TABLE product DROP COLUMN barcode') 