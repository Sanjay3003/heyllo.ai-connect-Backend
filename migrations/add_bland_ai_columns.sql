-- Add Bland AI integration columns to calls table
-- Run this SQL in your MySQL database

USE heyllo_db;  -- Replace with your actual database name

ALTER TABLE calls
ADD COLUMN external_call_id VARCHAR(100) NULL UNIQUE,
ADD COLUMN sentiment VARCHAR(20) NULL,
ADD COLUMN transcript TEXT NULL,
ADD COLUMN recording_url VARCHAR(500) NULL,
ADD COLUMN cost INT DEFAULT 0;

-- Add index for external_call_id for faster lookups
CREATE INDEX idx_calls_external_call_id ON calls(external_call_id);

-- Verify columns were added
DESCRIBE calls;
