"""
Inventory Agent - Domain Expert for Inventory Analysis
Provides domain hints for batches, stock levels, spoilage, and inventory movements.
Does NOT execute SQL - that's DatabaseAgent's job.
"""

from typing import Dict, Any, List
from core.logger import logger


class InventoryAgent:
    """
    Domain Expert for Inventory Analysis.
    
    Responsibilities:
    - Identify if query is inventory-related
    - Provide domain hints for batches, stock, spoilage, expiry
    - Support stockout risk and overstock calculations
    
    Does NOT:
    - Execute SQL queries
    - Connect to database directly
    
    Tables this expert knows about:
    - batches (primary - inventory snapshots)
    - batch_stock_tracking (stock movements)
    - spoilage_report (waste tracking)
    - perishable (shelf life info)
    - product_hierarchy (joins)
    - location (joins)
    """
    
    INVENTORY_KEYWORDS = [
        "inventory", "stock", "batch", "batches",
        "expir", "shelf life", "perishable",
        "spoil", "spoilage", "waste", "loss", "damage",
        "overstock", "stockout", "out of stock",
        "received", "transfer", "movement", "tracking",
        "current stock", "stock level", "stock at",
        "shrinkage", "shrink", "risk of shrinkage"  # Added for Q4-type queries
    ]
    
    def __init__(self):
        logger.info("📦 InventoryAgent initialized as domain expert")
    
    def can_handle(self, query: str) -> bool:
        """Check if this agent can provide domain hints for the query"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.INVENTORY_KEYWORDS)
    
    def get_domain_hints(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return domain-specific hints for SQL generation.
        This does NOT execute SQL - it provides context for DatabaseAgent.
        """
        query_lower = query.lower()
        
        hints = {
            "agent": "inventory",
            "domain": "inventory_analysis",
            "primary_table": "batches",
            "description": "Inventory management - batches, stock levels, spoilage, expiry tracking",
            
            # Table schemas
            "table_schema": """
-- BATCHES TABLE (Inventory Snapshots)
batches (
    batch_id VARCHAR,           -- Unique batch identifier
    product_code INTEGER,       -- FK to product_hierarchy.product_id
    store_code VARCHAR,         -- FK to location.location
    week_end_date DATE,         -- Snapshot date (joins with calendar.end_date)
    transfer_in_date DATE,      -- When batch was received
    expiry_date DATE,           -- Expiration date
    received_qty INTEGER,       -- Quantity received
    stock_at_week_start INTEGER,-- Stock at start of week
    stock_at_week_end INTEGER,  -- Stock at end of week (CURRENT STOCK)
    avg_daily_sales NUMERIC     -- Average daily sales rate
)

-- BATCH_STOCK_TRACKING TABLE (Stock Movements)
batch_stock_tracking (
    batch_id VARCHAR,           -- FK to batches.batch_id
    store_code VARCHAR,         -- FK to location.location
    transaction_date DATE,      -- Movement date
    transaction_type VARCHAR,   -- 'sale', 'transfer', 'adjustment', 'spoilage'
    quantity INTEGER,           -- Units moved
    running_balance INTEGER     -- Running stock balance
)

-- SPOILAGE_REPORT TABLE (Waste Tracking)
spoilage_report (
    product_code INTEGER,       -- FK to product_hierarchy.product_id
    store_code VARCHAR,         -- FK to location.location
    week_end_date DATE,         -- Report week
    spoilage_qty INTEGER,       -- Units spoiled
    spoilage_pct NUMERIC,       -- Spoilage percentage
    spoilage_value NUMERIC      -- Dollar value of spoilage
)

-- PERISHABLE TABLE (Shelf Life)
perishable (
    product VARCHAR,            -- Product name (joins with product_hierarchy.product)
    max_period TEXT,            -- Shelf life duration as TEXT (e.g., '7') - MUST CAST TO INTEGER!
    period_metric VARCHAR,      -- 'Days', 'Weeks', etc.
    storage_temp VARCHAR        -- 'Freezer', 'Refrigerator', 'Ambient'
)

⚠️ CRITICAL - PERISHABLE.MAX_PERIOD IS TEXT!
When doing arithmetic with max_period, ALWAYS cast to integer:
✅ CORRECT: CAST(p.max_period AS INTEGER) AS shelf_life_days
✅ CORRECT: CAST(p.max_period AS INTEGER) - some_numeric_value
❌ WRONG: p.max_period - some_numeric_value  (TEXT - NUMERIC causes error!)
""",
            
            # Key columns
            "key_columns": {
                "stock_at_week_end": "Current stock level (INTEGER) - USE THIS for current inventory",
                "stock_at_week_start": "Stock at beginning of week (INTEGER)",
                "expiry_date": "Batch expiration date (DATE)",
                "received_qty": "Quantity received in batch (INTEGER)",
                "spoilage_qty": "Units spoiled (INTEGER)",
                "spoilage_pct": "Spoilage percentage (NUMERIC)",
                "max_period": "Shelf life in days/weeks (INTEGER)"
            },
            
            # Join patterns
            "join_patterns": """
-- Batches Joins:
FROM batches b
JOIN product_hierarchy ph ON b.product_code = ph.product_id
JOIN location l ON b.store_code = l.location

-- With Perishable Info:
LEFT JOIN perishable p ON ph.product = p.product

-- Spoilage Joins:
FROM spoilage_report sr
JOIN product_hierarchy ph ON sr.product_code = ph.product_id
JOIN location l ON sr.store_code = l.location
""",
            
            # Formulas
            "formulas": [],
            
            # Time context
            "time_context": self._detect_time_context(query_lower)
        }
        
        # Current stock
        if any(word in query_lower for word in ["current stock", "stock level", "how much stock", "inventory level"]):
            hints["formulas"].append({
                "name": "Current Stock",
                "sql": "SUM(b.stock_at_week_end) AS current_stock",
                "description": "Current inventory level",
                "filter": "WHERE b.week_end_date = (SELECT MAX(week_end_date) FROM batches)"
            })
        
        # Expiring soon
        if any(word in query_lower for word in ["expir", "expiring soon", "about to expire", "shelf life"]):
            hints["formulas"].append({
                "name": "Days to Expiry",
                "sql": "(b.expiry_date - CURRENT_DATE) AS days_to_expiry",
                "description": "Days remaining until expiration"
            })
            hints["formulas"].append({
                "name": "Expiring Soon Filter",
                "sql": "b.expiry_date <= CURRENT_DATE + INTERVAL '7 days' AND b.expiry_date > CURRENT_DATE",
                "description": "Filter for items expiring within 7 days",
                "use_as": "WHERE clause"
            })
        
        # Shelf life risk (CFO formula)
        if any(word in query_lower for word in ["shelf life risk", "perishable loss", "expiry risk"]):
            hints["formulas"].append({
                "name": "Shelf-Life Risk Value",
                "sql": """
(b.stock_at_week_end - (b.avg_daily_sales * (b.expiry_date - '2025-11-08'::date))) 
* (SELECT AVG(s.total_amount) FROM sales s WHERE s.product_code = b.product_code) 
AS shelf_life_risk_value
""",
                "description": "Financial risk from products expiring before sale"
            })
        
        # Spoilage analysis
        if any(word in query_lower for word in ["spoil", "waste", "damaged", "loss"]):
            hints["formulas"].append({
                "name": "Total Spoilage",
                "sql": "SUM(sr.spoilage_qty) AS total_spoiled, AVG(sr.spoilage_pct) AS avg_spoilage_pct",
                "description": "Spoilage quantity and percentage"
            })
        
        # SHRINKAGE RISK - Q4 Type Query (heatwave + perishable + shrinkage)
        # This is CRITICAL for questions about "risk of shrinkage if we increase display"
        if any(word in query_lower for word in ["shrinkage", "shrink", "risk of shrinkage", "increase display", "meet demand", "perishable"]):
            hints["formulas"].append({
                "name": "Shrinkage Risk Analysis (with Daily Velocity + Shelf Life)",
                "sql": """
-- CRITICAL: For shrinkage/waste risk when increasing inventory:
-- Step 1: Calculate daily sales velocity (28-day average)
WITH daily_velocity AS (
    SELECT ph.product, l.region, l.market,
           SUM(s.sales_units) / 28.0 AS daily_sales_velocity
    FROM sales s
    JOIN product_hierarchy ph ON s.product_code = ph.product_id
    JOIN location l ON s.store_code = l.location
    WHERE s.transaction_date BETWEEN '2025-10-12' AND '2025-11-08'
    GROUP BY ph.product, l.region, l.market
),
-- Step 2: Get current inventory and shelf life (CAST max_period to INTEGER!)
current_inventory AS (
    SELECT ph.product, l.region, l.market,
           SUM(b.stock_at_week_end) AS current_stock,
           MAX(CAST(p.max_period AS INTEGER)) AS shelf_life_days,
           AVG('2025-11-08'::date - b.transfer_in_date) AS avg_age_days
    FROM batches b
    JOIN product_hierarchy ph ON b.product_code = ph.product_id
    JOIN location l ON b.store_code = l.location
    LEFT JOIN perishable p ON ph.product = p.product
    WHERE b.week_end_date = '2025-11-08'
    GROUP BY ph.product, l.region, l.market
),
-- Step 3: Calculate WDD impact from heatwave/cold spell
wdd_impact AS (
    SELECT m.product, l.region, l.market,
           (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) AS wdd_pct
    FROM metrics m
    JOIN location l ON m.location = l.location
    JOIN weekly_weather w ON w.week_end_date = m.end_date AND w.store_id = l.location
    WHERE m.end_date = '2025-11-15'
      AND (w.heatwave_flag = true OR w.cold_spell_flag = true)
    GROUP BY m.product, l.region, l.market
)
-- Final: Calculate shrinkage risk
SELECT 
    ci.product,
    ci.market,
    dv.daily_sales_velocity,
    ci.current_stock,
    ci.shelf_life_days,
    ROUND(ci.shelf_life_days - ci.avg_age_days, 1) AS days_until_expiry,
    ROUND(wi.wdd_pct * 100, 2) AS expected_demand_change_pct,
    -- Projected demand if display increased
    ROUND(dv.daily_sales_velocity * 7 * (1 + COALESCE(wi.wdd_pct, 0)), 0) AS projected_weekly_demand,
    -- Shrinkage risk: If increased stock exceeds what can sell before expiry
    CASE 
      WHEN ci.shelf_life_days - ci.avg_age_days > 0 THEN
        GREATEST(0, ci.current_stock - (dv.daily_sales_velocity * (ci.shelf_life_days - ci.avg_age_days)))
      ELSE ci.current_stock
    END AS potential_shrinkage_units,
    -- Shrinkage risk percentage
    CASE 
      WHEN ci.current_stock > 0 THEN
        ROUND(GREATEST(0, ci.current_stock - (dv.daily_sales_velocity * GREATEST(0, ci.shelf_life_days - ci.avg_age_days))) / ci.current_stock * 100, 2)
      ELSE 0
    END AS shrinkage_risk_pct
FROM current_inventory ci
LEFT JOIN daily_velocity dv ON ci.product = dv.product AND ci.market = dv.market
LEFT JOIN wdd_impact wi ON ci.product = wi.product AND ci.market = wi.market
""",
                "description": "Complete shrinkage risk analysis with velocity, inventory, shelf life, and WDD impact",
                "critical_for": "Q4 - Heatwave + perishable + shrinkage risk",
                "output_columns": ["daily_sales_velocity", "current_stock", "shelf_life_days", "days_until_expiry", "expected_demand_change_pct", "projected_weekly_demand", "potential_shrinkage_units", "shrinkage_risk_pct"]
            })
        
        # Stockout risk (CFO formula)
        if any(word in query_lower for word in ["stockout", "out of stock", "running out", "stockout risk"]):
            hints["formulas"].append({
                "name": "Stockout Risk Units",
                "sql": "GREATEST(0, (adjusted_velocity * 7) - current_stock) AS stockout_risk_units",
                "description": "Potential units short if demand exceeds stock",
                "requires_cte": True,
                "cte_hint": "Need adjusted_velocity from sales+metrics, current_stock from batches"
            })
        
        # Overstock (CFO formula)
        if any(word in query_lower for word in ["overstock", "excess", "too much stock"]):
            hints["formulas"].append({
                "name": "Overstock Percentage",
                "sql": "ROUND(((current_stock - adjusted_demand) / NULLIF(adjusted_demand, 0)) * 100, 2) AS overstock_pct",
                "description": "Percentage of stock above expected demand",
                "requires_cte": True,
                "cte_hint": "Need current_stock from batches, adjusted_demand from sales+metrics"
            })
        
        # Stock movements
        if any(word in query_lower for word in ["movement", "transfer", "tracking", "transaction"]):
            hints["formulas"].append({
                "name": "Stock Movement Summary",
                "sql": """
bst.transaction_type, 
SUM(CASE WHEN bst.quantity > 0 THEN bst.quantity ELSE 0 END) AS qty_in,
SUM(CASE WHEN bst.quantity < 0 THEN ABS(bst.quantity) ELSE 0 END) AS qty_out
""",
                "description": "Stock movements by type",
                "table": "batch_stock_tracking bst",
                "requires_groupby": "GROUP BY bst.transaction_type"
            })
        
        # Weeks of Cover (NEW - Testing Requirement)
        if any(word in query_lower for word in ["weeks of cover", "woc", "inventory duration", "how long", "risk level", "risk assessment", "availability risk", "low availability"]):
            hints["formulas"].append({
                "name": "Weeks of Cover (WOC) - Inventory Risk Assessment",
                "formula": "Current_Stock / Average_Weekly_Sales",
                "sql": "ROUND(current_stock / NULLIF(avg_weekly_sales, 0), 2) AS weeks_of_cover",
                "description": "How many weeks current inventory will last based on recent sales velocity",
                "requires_cte": True,
                "cte_hint": """
-- Calculate average weekly sales (last 4-6 weeks)
WITH weekly_sales AS (
  SELECT ph.product, l.location,
         AVG(week_sales.units) AS avg_weekly_sales
  FROM (
    SELECT s.product_code, s.store_code,
           DATE_TRUNC('week', s.transaction_date) AS week,
           SUM(s.sales_units) AS units
    FROM sales s
    WHERE s.transaction_date BETWEEN '2025-10-12' AND '2025-11-08'
    GROUP BY s.product_code, s.store_code, week
  ) week_sales
  JOIN product_hierarchy ph ON week_sales.product_code = ph.product_id
  JOIN location l ON week_sales.store_code = l.location
  GROUP BY ph.product, l.location
),
current_inventory AS (
  SELECT ph.product, l.location,
         SUM(b.stock_at_week_end) AS current_stock
  FROM batches b
  JOIN product_hierarchy ph ON b.product_code = ph.product_id
  JOIN location l ON b.store_code = l.location
  WHERE b.week_end_date = '2025-12-27'
  GROUP BY ph.product, l.location
)
"""
            })
            
            # Risk Level Categorization
            hints["formulas"].append({
                "name": "Risk Level Classification",
                "sql": """CASE 
  WHEN weeks_of_cover < 1 THEN 'HIGH RISK'
  WHEN weeks_of_cover < 2 THEN 'MEDIUM RISK'
  ELSE 'LOW RISK'
END AS risk_level""",
                "description": "Risk level based on weeks of cover: <1 week = HIGH, 1-2 weeks = MEDIUM, ≥2 weeks = LOW"
            })
            
            # Risk Priority Number
            hints["formulas"].append({
                "name": "Risk Priority (Numerical)",
                "sql": """CASE 
  WHEN weeks_of_cover < 1 THEN 1
  WHEN weeks_of_cover < 2 THEN 2
  ELSE 3
END AS risk_priority""",
                "description": "Numerical risk priority: 1 = High Risk, 2 = Medium Risk, 3 = Low Risk"
            })
        
        logger.info(f"📦 InventoryAgent provided {len(hints['formulas'])} inventory hints")
        return hints
    
    def _detect_time_context(self, query: str) -> Dict[str, Any]:
        """Detect time context from query"""
        context = {
            "current_week_end": "2025-11-08",
            "date_filter": "b.week_end_date = (SELECT MAX(week_end_date) FROM batches)",
            "use_latest": True
        }
        
        if any(word in query for word in ["last week", "previous"]):
            context["date_filter"] = "b.week_end_date = '2025-11-01'"
            context["use_latest"] = False
        
        return context
    
    def get_example_queries(self) -> List[str]:
        """Return example queries this agent can help with"""
        return [
            "What's the current stock level for Ice Cream?",
            "Show products expiring this week",
            "What's our spoilage rate by region?",
            "Which products have stockout risk?",
            "Show overstock percentage by store",
            "List batches received this month"
        ]


# Global instance
inventory_agent = InventoryAgent()
