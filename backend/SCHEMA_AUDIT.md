# 📊 PLANALYTICS DATABASE SCHEMA AUDIT
**Generated**: January 15, 2026  
**Purpose**: Verify all column names match between database, models, and prompts

---

## ✅ VERIFIED TABLES & COLUMNS

### 1. **calendar** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | INTEGER | Primary key | ✅ |
| `end_date` | DATE | Date joins, filtering | ✅ |
| `year` | INTEGER | Year filtering | ✅ |
| `quarter` | INTEGER | Quarterly analysis | ✅ |
| `month` | VARCHAR(50) | **STRING** ('January', 'February') | ✅ |
| `week` | INTEGER | Week number | ✅ |
| `season` | VARCHAR(20) | Seasonal analysis | ✅ |

**Critical Note**: 
- ⚠️ `month` is **STRING**, not INTEGER!
- Prompts correctly state: "calendar.month is STRING ('January', 'December') NOT integer!"

---

### 2. **product_hierarchy** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `product_id` | INTEGER | Primary key, joins with sales.product_code | ✅ |
| `dept` | VARCHAR(100) | Department grouping | ✅ |
| `category` | VARCHAR(100) | Category filtering | ✅ |
| `product` | VARCHAR(255) | Product name, joins with metrics.product | ✅ |

**Join Patterns**:
- ✅ `sales.product_code = product_hierarchy.product_id`
- ✅ `batches.product_code = product_hierarchy.product_id`
- ✅ `metrics.product = product_hierarchy.product`

---

### 3. **location** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | INTEGER | Primary key | ✅ |
| `location` | VARCHAR(50) | Store ID (e.g., 'ST0050') | ✅ |
| `region` | VARCHAR(100) | Region filtering (lowercase!) | ✅ |
| `market` | VARCHAR(100) | Market filtering | ✅ |
| `state` | VARCHAR(100) | State filtering | ✅ |
| `latitude` | NUMERIC | Geographic coordinates | ✅ |
| `longitude` | NUMERIC | Geographic coordinates | ✅ |

**Join Patterns**:
- ✅ `sales.store_code = location.location`
- ✅ `batches.store_code = location.location`
- ✅ `metrics.location = location.location`
- ✅ `events.store_id = location.location`

**Critical Note**:
- ⚠️ Region values are **LOWERCASE**: 'northeast', 'southeast', 'midwest', 'west', 'southwest'

---

### 4. **metrics** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | SERIAL | Primary key | ✅ |
| `product` | VARCHAR(255) | Product name (joins with product_hierarchy.product) | ✅ |
| `location` | VARCHAR(50) | Store ID (joins with location.location) | ✅ |
| `end_date` | DATE | Week ending date (joins with calendar.end_date) | ✅ |
| `metric` | NUMERIC | WDD value (weather-driven demand) | ✅ |
| `metric_nrm` | NUMERIC | Normal demand baseline | ✅ |
| `metric_ly` | NUMERIC | Last year demand | ✅ |

**WDD Formulas** (✅ Correct in prompts):
- Short-term (future): `(SUM(metric) - SUM(metric_nrm)) / NULLIF(SUM(metric_nrm), 0)`
- Long-term (past/YoY): `(SUM(metric) - SUM(metric_ly)) / NULLIF(SUM(metric_ly), 0)`

---

### 5. **sales** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | SERIAL | Primary key | ✅ |
| `batch_id` | VARCHAR(50) | Links to batches.batch_id | ✅ |
| `store_code` | VARCHAR(20) | Store ID (joins with location.location) | ✅ |
| `product_code` | INTEGER | Product ID (joins with product_hierarchy.product_id) | ✅ |
| `transaction_date` | DATE | Date of sale | ✅ |
| `sales_units` | INTEGER | Number of units sold | ✅ |
| `sales_amount` | NUMERIC(10,2) | Gross sales amount | ✅ |
| `discount_amount` | NUMERIC(10,2) | Discount applied | ✅ |
| `total_amount` | NUMERIC(10,2) | Net sales after discount | ✅ |

**Revenue Formula** (✅ Correct in prompts):
- **Total Units**: `SUM(sales_units)`
- **Revenue**: `SUM(sales_units * total_amount)` ← **CRITICAL!**

**Column Name Verification**:
- ✅ `transaction_date` (NOT `sale_date`)
- ✅ `sales_units` (NOT `quantity_sold`)
- ✅ `total_amount` (NOT `revenue`)

---

### 6. **batches** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | SERIAL | Primary key | ✅ |
| `batch_id` | VARCHAR(50) | Batch identifier | ✅ |
| `store_code` | VARCHAR(20) | Store ID | ✅ |
| `product_code` | INTEGER | Product ID | ✅ |
| `transaction_date` | DATE | Transaction date | ✅ |
| `expiry_date` | DATE | Expiration date | ✅ |
| `unit_price` | NUMERIC(10,2) | Price per unit | ✅ |
| `total_value` | NUMERIC(10,2) | Total batch value | ✅ |
| `received_qty` | INTEGER | Quantity received | ✅ |
| `mfg_date` | DATE | Manufacturing date | ✅ |
| `week_end_date` | DATE | Week ending date | ✅ |
| `stock_received` | INTEGER | Stock received this week | ✅ |
| `stock_at_week_start` | INTEGER | Stock at week start | ✅ |
| `stock_at_week_end` | INTEGER | Stock at week end | ✅ |

**Column Name Verification**:
- ✅ `stock_at_week_end` (NOT `current_qty`)
- ✅ `received_qty` (NOT `initial_qty`)

---

### 7. **batch_stock_tracking** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `record_id` | SERIAL | Primary key | ✅ |
| `batch_id` | VARCHAR(50) | Batch identifier | ✅ |
| `store_code` | VARCHAR(20) | Store ID | ✅ |
| `product_code` | INTEGER | Product ID | ✅ |
| `transaction_type` | VARCHAR(50) | Type: SALE, TRANSFER_IN, etc. | ✅ |
| `transaction_date` | DATE | Transaction date | ✅ |
| `qty_change` | INTEGER | Quantity changed | ✅ |
| `stock_after_transaction` | INTEGER | Stock after transaction | ✅ |
| `unit_price` | NUMERIC(10,2) | Unit price | ✅ |

---

### 8. **spoilage_report** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | SERIAL | Primary key | ✅ |
| `batch_id` | VARCHAR(50) | Batch identifier | ✅ |
| `store_code` | VARCHAR(20) | Store ID | ✅ |
| `product_code` | INTEGER | Product ID | ✅ |
| `qty` | INTEGER | Total quantity | ✅ |
| `spoilage_qty` | INTEGER | Quantity spoiled | ✅ |
| `spoilage_pct` | NUMERIC(5,2) | Spoilage percentage (0-100) | ✅ |
| `spoilage_case` | INTEGER | Severity (1-4) | ✅ |

**Column Name Verification**:
- ✅ No `report_date` column (previously incorrectly referenced)
- ✅ Only `spoilage_qty`, `spoilage_pct`, `spoilage_case`

---

### 9. **weekly_weather** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | INTEGER | Primary key | ✅ |
| `week_end_date` | DATE | Week ending date | ✅ |
| `avg_temp_f` | NUMERIC | Average temperature (°F) | ✅ |
| `temp_anom_f` | NUMERIC | Temperature anomaly (°F) | ✅ |
| `tmax_f` | NUMERIC | Maximum temperature (°F) | ✅ |
| `tmin_f` | NUMERIC | Minimum temperature (°F) | ✅ |
| `precip_in` | NUMERIC | Precipitation (inches) | ✅ |
| `precip_anom_in` | NUMERIC | Precipitation anomaly (inches) | ✅ |
| `heatwave_flag` | BOOLEAN | Heatwave indicator | ✅ |
| `cold_spell_flag` | BOOLEAN | Cold spell indicator | ✅ |
| `heavy_rain_flag` | BOOLEAN | Heavy rain indicator | ✅ |
| `snow_flag` | BOOLEAN | Snow indicator | ✅ |
| `store_id` | VARCHAR(50) | Store ID | ✅ |

**Join Pattern**:
- ✅ `weekly_weather.week_end_date = calendar.end_date AND weekly_weather.store_id = location.location`

**Table Name Verification**:
- ✅ Table name is `weekly_weather` (NOT `weather_data`)
- ✅ Prompts correctly reference `weekly_weather`

---

### 10. **events** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | INTEGER | Primary key | ✅ |
| `event` | VARCHAR(255) | Event name | ✅ |
| `event_type` | VARCHAR(100) | Event type/category | ✅ |
| `event_date` | DATE | Event date | ✅ |
| `store_id` | VARCHAR(50) | Store ID (joins with location.location) | ✅ |
| `region` | VARCHAR(100) | Region | ✅ |
| `market` | VARCHAR(100) | Market | ✅ |
| `state` | VARCHAR(100) | State | ✅ |

---

### 11. **perishable** Table ✅
**Status**: All columns match correctly

| Column | Type | Usage in Prompts | Status |
|--------|------|------------------|--------|
| `id` | INTEGER | Primary key | ✅ |
| `product` | VARCHAR(255) | Product name | ✅ |
| `perishable_id` | INTEGER | Perishable identifier | ✅ |
| `min_period` | VARCHAR(50) | Minimum shelf life period | ✅ |
| `max_period` | VARCHAR(50) | Maximum shelf life period | ✅ |
| `period_metric` | VARCHAR(50) | Period metric | ✅ |
| `storage` | VARCHAR(100) | Storage requirements | ✅ |

---

## 🔍 CRITICAL FINDINGS

### ✅ ALL CORRECT
1. **Revenue Formula**: `SUM(sales_units * total_amount)` ✅
2. **Table Name**: `weekly_weather` (not weather_data) ✅
3. **Column Names**: All database columns match prompt references ✅
4. **Join Patterns**: All documented correctly ✅

### ⚠️ CRITICAL REMINDERS
1. **calendar.month** is STRING, not INTEGER
2. **location.region** values are LOWERCASE ('northeast', not 'Northeast')
3. **batches.stock_at_week_end** (not current_qty)
4. **sales.transaction_date** (not sale_date)
5. **spoilage_report** has NO date column

---

## 📝 TESTING TEAM LOGIC PATTERNS

According to error.txt, these are the required patterns:

1. **SALES** → Use `sales` table only
2. **EVENT+SALES** → Join `events` + `sales` tables
3. **WDD-NRM** → Use `metrics` table with `metric` vs `metric_nrm`
4. **WDD-NRM + sales** → Join `metrics` + `sales` tables
5. **WDD-NRM+SALES** → Join `metrics` + `sales` tables
6. **WDD_LY + sales** → Use `metrics` table with `metric` vs `metric_ly` + `sales`

### Formulas (✅ All Correct in Prompts):
- **Total Units**: `SUM(sales_units)`
- **Revenue**: `SUM(sales_units * total_amount)`
- **WDD-NRM**: `(metric - metric_nrm) / metric_nrm * 100`
- **WDD-LY**: `(metric - metric_ly) / metric_ly * 100`
- **Recommended Order**: `metric_nrm * (1 + WDD_change)`

---

## ✅ CONCLUSION

**ALL DATABASE COLUMNS ARE CORRECTLY REFERENCED IN PROMPTS!**

No schema mismatches found. The system is ready for testing team validation.

---

## 🎯 NEXT STEPS FOR CALL

1. ✅ Schema verified - all columns match
2. ✅ Formulas verified - revenue calculation correct
3. ✅ Table names verified - weekly_weather is correct
4. 🔜 Review individual questions with testing team
5. 🔜 Validate query logic against testing patterns

**You're ready for the call! All foundational data is correct.**
