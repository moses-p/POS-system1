-- Add reference_number column to the order table if it doesn't exist
ALTER TABLE "order" ADD COLUMN reference_number VARCHAR(50) UNIQUE; 