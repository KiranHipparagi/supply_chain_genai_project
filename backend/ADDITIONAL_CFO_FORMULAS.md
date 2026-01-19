# Additional CFO-Level Business Formulas - Integration Complete ✅

## Overview
Successfully integrated **7 additional advanced CFO-level business formulas** from `additional_formulas.txt` into the chatbot's SQL generation prompts. These formulas enable sophisticated regional analysis, stockout tracking, and financial risk assessment.

**Date**: January 17, 2026  
**Integration Locations**:
- ✅ [backend/agents/database_agent.py](backend/agents/database_agent.py) - Lines ~265-460
- ✅ [backend/services/context_resolver.py](backend/services/context_resolver.py) - Lines ~1480-1680

## Previously Integrated Formulas (First Phase)
The following 10 formulas were integrated earlier:
1. Daily Sales Velocity
2. Adjusted Velocity
3. Adjusted Demand
4. Stockout Loss (per product)
5. Week-on-Week Sales Change
6. Sales Uplift vs 4-Week Average
7. Overstock Percentage
8. Shelf-Life Risk
9. Stockout Rate
10. Predicted Total Loss

## Newly Added Formulas (Second Phase)

### 11. Highest Overstock Percentage by Region
- **Formula**: `((Current_Stock - Adjusted_Demand) / NULLIF(Adjusted_Demand, 0)) × 100`
- **Purpose**: Identify regions with excess inventory requiring promotions/redistribution
- **Use Case**: "Which region has the highest overstock percentage this week?"
- **Business Impact**: Helps CFOs identify surplus inventory that may require markdowns or redistribution
- **Key Components**:
  - Current_Stock = stock_at_week_start (inventory snapshot at start of week)
  - Adjusted_Demand = Avg_4Week_Sales × (1 + WDD_Pct_vs_Normal)
- **SQL Example**:
  ```sql
  WITH adjusted_demand AS (
      SELECT l.region, 
             SUM(b.stock_at_week_start) AS total_stock,
             SUM(s.avg_4week_sales * (1 + (m.metric - m.metric_nrm) / NULLIF(m.metric_nrm, 0))) AS total_adjusted_demand
      FROM batches b
      JOIN location l ON b.store_code = l.location
      JOIN metrics m ON b.product_code::text = m.product AND b.store_code = m.location
      JOIN (SELECT product_code, store_code, AVG(sales_units) as avg_4week_sales 
            FROM sales WHERE transaction_date >= CURRENT_DATE - INTERVAL '28 days'
            GROUP BY product_code, store_code) s 
        ON b.product_code = s.product_code AND b.store_code = s.store_code
      GROUP BY l.region
  )
  SELECT region, 
         ((total_stock - total_adjusted_demand) / NULLIF(total_adjusted_demand, 0)) * 100 AS overstock_pct
  FROM adjusted_demand
  ORDER BY overstock_pct DESC LIMIT 1;
  ```

---

### 12. Highest Weather-Driven Stockout Loss by Region
- **Formula**: `Total_Regional_Loss = SUM(MAX(0, (Adjusted_Velocity × 7) - Current_Stock))`
- **Purpose**: Identify which region experienced the highest revenue loss from stockouts
- **Use Case**: "Which region had the highest stockout loss this week?"
- **Business Impact**: Quantifies lost revenue opportunity due to insufficient inventory, helps prioritize regional restocking
- **Key Components**:
  - Daily_Sales_Velocity = Total_Sales_Last_28_Days / 28
  - Pct_vs_Normal = (Metric - Metric_NRM) / NULLIF(Metric_NRM, 0)
  - Adjusted_Velocity = Daily_Sales_Velocity × (1 + Pct_vs_Normal)
  - Current_Stock = stock_at_week_end
- **SQL Example**:
  ```sql
  WITH velocity AS (
      SELECT product_code, store_code, SUM(sales_units) / 28.0 AS daily_velocity
      FROM sales WHERE transaction_date >= CURRENT_DATE - INTERVAL '28 days'
      GROUP BY product_code, store_code
  ),
  losses AS (
      SELECT l.region,
             SUM(GREATEST(0, 
                 (v.daily_velocity * (1 + (m.metric - m.metric_nrm) / NULLIF(m.metric_nrm, 0)) * 7) 
                 - b.stock_at_week_end
             )) AS total_loss_units
      FROM batches b
      JOIN location l ON b.store_code = l.location
      JOIN velocity v ON b.product_code = v.product_code AND b.store_code = v.store_code
      JOIN metrics m ON b.product_code::text = m.product AND b.store_code = m.location
      GROUP BY l.region
  )
  SELECT region, total_loss_units
  FROM losses
  ORDER BY total_loss_units DESC LIMIT 1;
  ```

---

### 13. Total Units Lost Across All Regions Due to Stockouts
- **Formula**: `Total_Lost_Units = SUM(MAX(0, (Expected_Sales - Actual_Sales)))`
- **Purpose**: Aggregate all unmet demand to show total business impact
- **Use Case**: "How many total units did we lose to stockouts across all regions this week?"
- **Business Impact**: Provides company-wide view of stockout impact, helps CFO understand total revenue at risk
- **Key Components**:
  - Daily_Velocity = Total_Sales_Last_28_Days / 28
  - Expected_Sales_Week = Daily_Velocity × 7
  - Lost_Units = MAX(0, Expected_Sales - Actual_Sales)
- **SQL Example**:
  ```sql
  WITH expected AS (
      SELECT product_code, store_code,
             (SUM(sales_units) / 28.0) * 7 AS expected_weekly_sales
      FROM sales 
      WHERE transaction_date >= CURRENT_DATE - INTERVAL '28 days'
      GROUP BY product_code, store_code
  ),
  actual AS (
      SELECT product_code, store_code, SUM(sales_units) AS actual_weekly_sales
      FROM sales
      WHERE transaction_date BETWEEN CURRENT_DATE - INTERVAL '7 days' AND CURRENT_DATE
      GROUP BY product_code, store_code
  )
  SELECT SUM(GREATEST(0, e.expected_weekly_sales - COALESCE(a.actual_weekly_sales, 0))) AS total_lost_units
  FROM expected e
  LEFT JOIN actual a ON e.product_code = a.product_code AND e.store_code = a.store_code;
  ```

---

### 14. Highest Predicted Loss from Shelf-Life Risk and Overstock
- **Formula**: `Total_Loss = Shelf_Life_Loss + Overstock_Markdown_Loss`
- **Purpose**: Total predicted financial loss from waste and markdowns per region
- **Use Case**: "Which region has the highest predicted loss from expiring stock and overstock?"
- **Business Impact**: Comprehensive risk assessment combining perishable waste and markdown exposure
- **Key Components**:
  - Shelf_Life_Loss (expiring) = (Stock - (Avg_Daily_Sales × Days_to_Expiry)) × Unit_Price
  - Shelf_Life_Loss (expired) = Stock × Unit_Price (when days_to_expiry ≤ 0)
  - Overstock_Loss = (Stock - (Adjusted_Demand × 2)) × Unit_Price × 0.30
  - Total = Shelf_Life_Loss + Overstock_Loss
- **SQL Example**:
  ```sql
  WITH shelf_loss AS (
      SELECT l.region,
             SUM(CASE 
                 WHEN (b.expiry_date - CURRENT_DATE) > 0 
                 THEN GREATEST(0, b.stock_at_week_end - (v.daily_velocity * (b.expiry_date - CURRENT_DATE))) * b.unit_price
                 ELSE b.stock_at_week_end * b.unit_price
             END) AS shelf_life_loss
      FROM batches b
      JOIN location l ON b.store_code = l.location
      JOIN (SELECT product_code, store_code, SUM(sales_units)/28.0 AS daily_velocity 
            FROM sales WHERE transaction_date >= CURRENT_DATE - INTERVAL '28 days'
            GROUP BY product_code, store_code) v
        ON b.product_code = v.product_code AND b.store_code = v.store_code
      GROUP BY l.region
  ),
  overstock_loss AS (
      SELECT l.region,
             SUM(GREATEST(0, b.stock_at_week_end - (adj.adjusted_demand * 2)) * b.unit_price * 0.30) AS overstock_markdown
      FROM batches b
      JOIN location l ON b.store_code = l.location
      JOIN (SELECT product_code, store_code,
                   AVG(sales_units) * (1 + (m.metric - m.metric_nrm)/NULLIF(m.metric_nrm, 0)) AS adjusted_demand
            FROM sales s JOIN metrics m ON s.product_code::text = m.product AND s.store_code = m.location
            WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
            GROUP BY product_code, store_code, m.metric, m.metric_nrm) adj
        ON b.product_code = adj.product_code AND b.store_code = adj.store_code
      GROUP BY l.region
  )
  SELECT sl.region, 
         (sl.shelf_life_loss + ol.overstock_markdown) AS total_predicted_loss
  FROM shelf_loss sl
  JOIN overstock_loss ol ON sl.region = ol.region
  ORDER BY total_predicted_loss DESC LIMIT 1;
  ```

---

### 15. Week-by-Week Stockout Rate
- **Formula**: `Stockout_Rate = (SKUs_with_Zero_Stock / Total_SKUs) × 100`
- **Purpose**: Monitor product availability trends over time
- **Use Case**: "Show me stockout rates for the past 8 weeks"
- **Business Impact**: Track whether stockout situation is improving or worsening over time
- **SQL Example**:
  ```sql
  WITH weekly_stockouts AS (
      SELECT c.end_date,
             COUNT(CASE WHEN b.stock_at_week_end = 0 THEN 1 END) AS zero_stock_skus,
             COUNT(*) AS total_skus
      FROM batches b
      JOIN calendar c ON b.week_end_date = c.end_date
      WHERE c.end_date BETWEEN CURRENT_DATE - INTERVAL '8 weeks' AND CURRENT_DATE
      GROUP BY c.end_date
  )
  SELECT end_date,
         (zero_stock_skus::NUMERIC / NULLIF(total_skus, 0)) * 100 AS stockout_rate_pct
  FROM weekly_stockouts
  ORDER BY end_date;
  ```

---

### 16. Week-by-Week Stockout Rate Change
- **Formula**: `WoW_Change = Stockout_Rate_Current_Week - Stockout_Rate_Previous_Week`
- **Purpose**: Track whether stockout situation is improving or worsening
- **Use Case**: "Did stockout rates improve this week compared to last week?"
- **Business Impact**: Early warning system for supply chain deterioration or improvement
- **SQL Example**:
  ```sql
  WITH weekly_rates AS (
      SELECT c.end_date,
             (COUNT(CASE WHEN b.stock_at_week_end = 0 THEN 1 END)::NUMERIC / 
              NULLIF(COUNT(*), 0)) * 100 AS stockout_rate
      FROM batches b
      JOIN calendar c ON b.week_end_date = c.end_date
      WHERE c.end_date IN (CURRENT_DATE, CURRENT_DATE - INTERVAL '7 days')
      GROUP BY c.end_date
  )
  SELECT 
      MAX(CASE WHEN end_date = CURRENT_DATE THEN stockout_rate END) -
      MAX(CASE WHEN end_date = CURRENT_DATE - INTERVAL '7 days' THEN stockout_rate END) 
      AS wow_stockout_change_pct
  FROM weekly_rates;
  ```

---

### 17. Loss Due to Stockouts of Top 10 Fastest-Selling SKUs
- **Formula**: `Lost_Units_per_SKU = MAX(0, Expected_Weekly_Velocity - Actual_Weekly_Sales)`
- **Purpose**: Prioritize restocking for highest-impact products
- **Use Case**: "Which fast-selling products had the biggest stockout losses this week?"
- **Business Impact**: Focus attention on SKUs where stockouts have the greatest revenue impact
- **Key Components**:
  - Expected_Weekly_Velocity = (28_Day_Sales / 28) × 7
  - Top 10 = Ranked by 28-day sales velocity
  - Lost_Units = Expected - Actual (for SKUs with stock at week end = 0)
- **SQL Example**:
  ```sql
  WITH top_velocity AS (
      SELECT product_code, store_code, SUM(sales_units) AS total_28day_sales
      FROM sales
      WHERE transaction_date >= CURRENT_DATE - INTERVAL '28 days'
      GROUP BY product_code, store_code
      ORDER BY total_28day_sales DESC
      LIMIT 10
  ),
  expected AS (
      SELECT tv.product_code, tv.store_code,
             (tv.total_28day_sales / 28.0) * 7 AS expected_weekly_velocity
      FROM top_velocity tv
  ),
  actual AS (
      SELECT product_code, store_code, SUM(sales_units) AS actual_weekly_sales
      FROM sales
      WHERE transaction_date BETWEEN CURRENT_DATE - INTERVAL '7 days' AND CURRENT_DATE
      GROUP BY product_code, store_code
  )
  SELECT e.product_code, e.store_code, p.product, l.location,
         GREATEST(0, e.expected_weekly_velocity - COALESCE(a.actual_weekly_sales, 0)) AS lost_units
  FROM expected e
  LEFT JOIN actual a ON e.product_code = a.product_code AND e.store_code = a.store_code
  JOIN product_hierarchy p ON e.product_code = p.product_id
  JOIN location l ON e.store_code = l.location
  ORDER BY lost_units DESC
  LIMIT 10;
  ```

---

## Updated Formula Usage Guidelines

### When to Use (Enhanced):
- **Regional analysis** / "which region" → Use formulas #11, #12, #14
- **Stockout trends** / "availability tracking" → Use formulas #15, #16
- **Top products** / "fastest selling" / "high velocity SKUs" → Use formula #17
- **Company-wide impact** / "total business loss" → Use formula #13
- **Inventory optimization** / "overstock" → Use formulas #7, #11
- **Financial risk** / "total loss" → Use formulas #10, #14
- **Stockout risk** / "running out" → Use formulas #4, #12, #13

---

## Integration Details

### Files Modified:
1. **backend/agents/database_agent.py**
   - Added formulas #11-17 after formula #10
   - Updated "WHEN TO USE CFO FORMULAS" section with new formula references
   - Total CFO formulas now: **17 formulas** (previously 10)

2. **backend/services/context_resolver.py**
   - Added formulas #11-17 with PostgreSQL-specific examples
   - Updated "WHEN TO USE CFO FORMULAS" section with enhanced categorization
   - Maintains consistency with database_agent.py

### Testing Recommendations:

#### Test Query Examples:
1. **Regional Overstock**: "Which region has the highest overstock percentage this week?"
2. **Regional Stockout Loss**: "Show me which region lost the most sales due to stockouts"
3. **Total Company Loss**: "How many total units did we lose to stockouts across all regions?"
4. **Comprehensive Risk**: "Which region has the highest predicted loss from expiring stock and overstock?"
5. **Stockout Trends**: "Show me stockout rates for the past 8 weeks"
6. **Stockout Improvement**: "Did stockout rates improve this week?"
7. **High-Velocity SKU Losses**: "Which fast-selling products had the biggest stockout losses?"

#### Expected Behavior:
- LLM should recognize regional analysis keywords and use formulas #11, #12, #14
- LLM should recognize stockout trend queries and use formulas #15, #16
- LLM should identify "top products" or "fastest selling" and use formula #17
- LLM should aggregate company-wide metrics with formula #13
- SQL generated should include proper JOINs, CTEs, and aggregations

---

## Business Value

### CFO-Level Insights Enabled:
1. **Regional Performance Comparison**: Identify best/worst performing regions
2. **Stockout Trend Analysis**: Early warning for supply chain issues
3. **High-Impact SKU Prioritization**: Focus on products that matter most
4. **Comprehensive Risk Assessment**: Complete view of inventory financial exposure
5. **Company-Wide Aggregation**: Executive dashboard metrics

### Financial Impact:
- **Reduced Stockouts**: Better identification of high-risk regions/SKUs
- **Optimized Inventory**: Faster identification of overstock requiring action
- **Minimized Waste**: Comprehensive loss prediction from expiry + markdown
- **Data-Driven Decisions**: Quantified financial impact for prioritization

---

## Version History

### Phase 1 (Previous Integration):
- **Date**: January 15-16, 2026
- **Formulas**: #1-10 (Daily Velocity, Adjusted Velocity, Stockout Loss, etc.)
- **Focus**: Product-level and basic analytics

### Phase 2 (Current Integration):
- **Date**: January 17, 2026
- **Formulas**: #11-17 (Regional analysis, stockout trends, high-velocity SKU focus)
- **Focus**: Regional aggregation, trend analysis, executive-level insights

---

## Total Formula Count: **17 CFO-Level Business Formulas** ✅

All formulas now available in both:
- [backend/agents/database_agent.py](backend/agents/database_agent.py)
- [backend/services/context_resolver.py](backend/services/context_resolver.py)

**Status**: Integration Complete and Ready for Testing
