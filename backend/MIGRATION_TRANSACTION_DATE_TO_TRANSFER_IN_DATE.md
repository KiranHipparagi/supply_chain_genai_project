# Database Column Rename: transaction_date → transfer_in_date

## Context
The office laptop (production) PostgreSQL database uses `transfer_in_date` instead of `transaction_date` for the batches table. This change aligns the local development environment with production.

## Scope
**ONLY the `batches` table** is affected. Other tables keep their `transaction_date` columns:
- ✅ `sales.transaction_date` - **NOT CHANGED** (remains as-is)
- ✅ `batch_stock_tracking.transaction_date` - **NOT CHANGED** (remains as-is)
- 🔄 `batches.transaction_date` → **RENAMED to** `batches.transfer_in_date`

## Changes Made

### 1. SQLAlchemy Model Updated ✅
**File**: `backend/database/postgres_db.py`
- Changed `Batches` model column from `transaction_date` to `transfer_in_date`

### 2. Database Agent Prompt Updated ✅
**File**: `backend/agents/database_agent.py`
- Updated batches table schema documentation in system prompt
- Changed from `transaction_date` to `transfer_in_date`

### 3. Context Resolver Prompt Updated ✅
**File**: `backend/services/context_resolver.py`
- Updated batches table schema documentation
- Changed from `transaction_date` to `transfer_in_date`

### 4. Migration Script Created ✅
**File**: `backend/planalytics_postgres/migrate_transaction_date_to_transfer_in_date.sql`
- SQL script to rename the column in PostgreSQL database

## How to Apply Changes

### Step 1: Run the Database Migration

```bash
cd /home/kiran/Documents/planalytics-genai-solution/backend

# Run the migration script
PGPASSWORD='password' psql -h localhost -U postgres -d planalytics_database \
  -f planalytics_postgres/migrate_transaction_date_to_transfer_in_date.sql
```

### Step 2: Verify the Migration

```bash
# Check that the column was renamed
PGPASSWORD='password' psql -h localhost -U postgres -d planalytics_database \
  -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'batches' AND column_name = 'transfer_in_date';"
```

**Expected output:**
```
 column_name      | data_type 
------------------+-----------
 transfer_in_date | date
```

### Step 3: Restart Your Backend Server

```bash
cd /home/kiran/Documents/planalytics-genai-solution/backend
./venv/bin/python main.py
```

## What This Fixes

1. ✅ **Alignment with Production**: Local database now matches office laptop schema
2. ✅ **Clearer Semantics**: `transfer_in_date` better describes when inventory was received/transferred
3. ✅ **No Code Breakage**: All Python code updated to use new column name
4. ✅ **SQL Generation**: LLM prompts updated to generate correct SQL with `transfer_in_date`

## Important Notes

### Tables NOT Affected:
- **sales table**: Still uses `transaction_date` (date of sale) ✓
- **batch_stock_tracking table**: Still uses `transaction_date` (date of movement) ✓

### Only Batches Table Changed:
- Old: `batches.transaction_date`
- New: `batches.transfer_in_date`

## Rollback (If Needed)

If you need to revert the change:

```sql
-- Rollback migration
ALTER TABLE batches 
RENAME COLUMN transfer_in_date TO transaction_date;
```

Then revert the code changes in:
- `backend/database/postgres_db.py`
- `backend/agents/database_agent.py`
- `backend/services/context_resolver.py`

## Testing Checklist

After applying changes:

- [ ] Database migration completed successfully
- [ ] Backend server starts without errors
- [ ] Inventory queries work (batch expiry, stock levels)
- [ ] SQL generation uses `transfer_in_date` correctly
- [ ] No errors in application logs

## Column Naming Convention Summary

| Table | Column Name | Purpose |
|-------|-------------|---------|
| sales | `transaction_date` | Date of sale transaction |
| batch_stock_tracking | `transaction_date` | Date of stock movement |
| batches | `transfer_in_date` | Date batch was received/transferred |

---

**Status**: ✅ Code updated, ready for database migration
**Next Step**: Run the migration SQL script above
