-- Migration Script: Rename batches.transaction_date to batches.transfer_in_date
-- Purpose: Align local database schema with production (office laptop) database
-- Date: January 16, 2026

-- Step 1: Rename the column in batches table
ALTER TABLE batches 
RENAME COLUMN transaction_date TO transfer_in_date;

-- Step 2: Verify the change
\d batches

-- Step 3: Update any indexes (if needed)
-- The existing indexes on transaction_date will automatically be renamed

-- Verification query - check that transfer_in_date exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'batches' 
AND column_name = 'transfer_in_date';

-- Expected result: Should show transfer_in_date with data_type = 'date'
