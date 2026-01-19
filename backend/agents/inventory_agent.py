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
        "current stock", "stock level", "stock at"
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
    max_period INTEGER,         -- Shelf life duration
    period_metric VARCHAR,      -- 'Days', 'Weeks', etc.
    storage_temp VARCHAR        -- 'Freezer', 'Refrigerator', 'Ambient'
)
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
