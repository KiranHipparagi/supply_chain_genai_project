# 🎯 QUICK REFERENCE - CALL PREPARATION

## ✅ VERIFIED STATUS
**All database schemas match prompts perfectly!** No column name errors.

---

## 📊 CRITICAL FORMULAS (All Correct ✅)

```sql
-- Revenue (ALWAYS use this!)
Revenue = SUM(sales_units * total_amount)

-- Total Units
Total_Units = SUM(sales_units)

-- WDD Short-term (≤4 weeks, FUTURE queries)
WDD_NRM = (SUM(metric) - SUM(metric_nrm)) / NULLIF(SUM(metric_nrm), 0) * 100

-- WDD Long-term (>4 weeks, PAST/YoY queries)
WDD_LY = (SUM(metric) - SUM(metric_ly)) / NULLIF(SUM(metric_ly), 0) * 100

-- Recommended Order
Recommended_Order = metric_nrm * (1 + WDD_change)
```

---

## 🗂️ TABLE QUICK REFERENCE

### Main Tables & Their Purpose

| Table | Use For | Key Columns |
|-------|---------|-------------|
| **sales** | Actual transactions, revenue | `sales_units`, `total_amount`, `transaction_date` |
| **metrics** | WDD demand trends | `metric`, `metric_nrm`, `metric_ly` |
| **batches** | Inventory levels | `stock_at_week_end`, `expiry_date` |
| **spoilage_report** | Waste analysis | `spoilage_qty`, `spoilage_pct` |
| **weekly_weather** | Weather flags | `heatwave_flag`, `cold_spell_flag` |
| **events** | Event impact | `event`, `event_type`, `event_date` |
| **location** | Geographic data | `location`, `region`, `market` |
| **product_hierarchy** | Product data | `product_id`, `product`, `category` |
| **calendar** | Date dimensions | `end_date`, `week`, `month`, `season` |

---

## 🔗 CRITICAL JOIN PATTERNS

```sql
-- Sales joins
sales.store_code = location.location
sales.product_code = product_hierarchy.product_id
sales.transaction_date = calendar.end_date

-- Metrics joins
metrics.location = location.location
metrics.product = product_hierarchy.product
metrics.end_date = calendar.end_date

-- Weather joins
weekly_weather.store_id = location.location
weekly_weather.week_end_date = calendar.end_date

-- Events joins
events.store_id = location.location
```

---

## ⚠️ CRITICAL GOTCHAS

### 1. Column Name Traps
| ❌ WRONG | ✅ CORRECT |
|----------|------------|
| `current_qty` | `stock_at_week_end` |
| `sale_date` | `transaction_date` |
| `quantity_sold` | `sales_units` |
| `weather_data` table | `weekly_weather` table |
| `calendar.month = 11` | `calendar.month = 'November'` |

### 2. Data Type Traps
- `calendar.month` is **STRING** ('January', 'February') NOT INTEGER
- `location.region` values are **LOWERCASE** ('northeast', not 'Northeast')
- `product_code` is **INTEGER** (use `=`, not `LIKE`)

### 3. Revenue Formula Trap
- ❌ WRONG: `SUM(total_amount)`
- ✅ CORRECT: `SUM(sales_units * total_amount)`

---

## 📋 TESTING TEAM PATTERNS

| Pattern | Tables Used | Example |
|---------|-------------|---------|
| **1. SALES** | `sales` only | Q1: Miami beach food diversification |
| **2. EVENT+SALES** | `events` + `sales` | Q2: Columbia SC sales rise |
| **3. WDD-NRM** | `metrics` (metric vs nrm) | Q3: Northeast cold spell |
| **4. WDD-NRM+sales** | `metrics` + `sales` | Q4: SF heatwave perishables |
| **5. WDD-NRM+SALES** | `metrics` + `sales` | Q5: Tampa 7-day ordering |
| **6. WDD_LY+sales** | `metrics` (metric vs ly) + `sales` | Q6: Spring allergy relief |

---

## 🎤 WHAT TO SAY IN CALL

### If they ask about schema:
> "All column names have been verified against the actual PostgreSQL database. The prompts correctly reference all tables and columns."

### If they ask about formulas:
> "Revenue formula is confirmed: `SUM(sales_units * total_amount)`. WDD formulas use metric vs metric_nrm for short-term and metric vs metric_ly for year-over-year."

### If they want to update prompts:
> "We can update two key files:
> 1. `database_agent.py` - Main SQL generation prompt (lines 36-515)
> 2. `context_resolver.py` - Context-aware prompt (lines 210-1199)
>
> Just tell me what changes you need and I'll implement them immediately."

### If they mention wrong table usage:
> "We can add explicit table selection rules in the prompt. For example, if the question is about 'sales performance', force the use of the sales table instead of metrics table."

---

## 🚀 FILES TO OPEN DURING CALL

1. **database_agent.py** - Main SQL prompt
   - Path: `/home/kiran/Documents/planalytics-genai-solution/backend/agents/database_agent.py`
   - Lines 36-515: System prompt

2. **context_resolver.py** - Context-enhanced prompt
   - Path: `/home/kiran/Documents/planalytics-genai-solution/backend/services/context_resolver.py`
   - Lines 210-1199: `get_sql_generation_prompt` method

3. **error.txt** - Test questions
   - Path: `/home/kiran/Documents/planalytics-genai-solution/error.txt`
   - Contains all 6 test questions with expected logic

---

## 🔧 RESTART SERVER COMMAND

```bash
cd /home/kiran/Documents/planalytics-genai-solution/backend && ./venv/bin/python main.py
```

---

## ✅ YOU'RE READY!

All schemas verified ✅  
All formulas correct ✅  
All tables documented ✅  
Quick edits ready ✅  

**Just tell me what they want to change during the call!** 🎯
