"""
Sales Agent - Domain Expert for Sales Analysis
Provides domain hints, formulas, and column information for sales-related queries.
Does NOT execute SQL - that's DatabaseAgent's job.
"""

from typing import Dict, Any, List
from core.logger import logger


class SalesAgent:
    """
    Domain Expert for Sales Analysis.
    
    Responsibilities:
    - Identify if query is sales-related
    - Provide domain hints (columns, formulas, join patterns)
    - Return context for SQL generation
    
    Does NOT:
    - Execute SQL queries
    - Connect to database directly
    
    Tables this expert knows about:
    - sales (primary)
    - product_hierarchy (joins)
    - location (joins)  
    - calendar (joins)
    """
    
    # Domain keywords that indicate sales queries
    SALES_KEYWORDS = [
        "sales", "sold", "selling", "revenue", "units sold",
        "top selling", "best selling", "fastest growing",
        "sales performance", "sales trend", "sales change",
        "discount", "total amount", "gross sales",
        "how did", "perform", "performance", "transaction",
        "week-on-week", "wow", "sales uplift", "sales velocity"
    ]
    
    # Keywords that should NOT go to sales agent (WDD is different)
    EXCLUDE_KEYWORDS = [
        "wdd", "weather-driven demand", "forecast demand",
        "weather impact on demand", "adjusted demand", "adjusted velocity",
        "metric_nrm", "metric_ly"
    ]
    
    def __init__(self):
        logger.info("📊 SalesAgent initialized as domain expert")
    
    def can_handle(self, query: str) -> bool:
        """Check if this agent can provide domain hints for the query"""
        query_lower = query.lower()
        
        has_sales_keyword = any(kw in query_lower for kw in self.SALES_KEYWORDS)
        has_exclude_keyword = any(kw in query_lower for kw in self.EXCLUDE_KEYWORDS)
        
        return has_sales_keyword and not has_exclude_keyword
    
    def get_domain_hints(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return domain-specific hints for SQL generation.
        This does NOT execute SQL - it provides context for DatabaseAgent.
        """
        query_lower = query.lower()
        
        hints = {
            "agent": "sales",
            "domain": "sales_analysis",
            "primary_table": "sales",
            "description": "Sales transaction analysis - actual revenue and units sold from transactions",
            
            # Table schema hints
            "table_schema": """
-- SALES TABLE (Actual Transactions)
sales (
    product_code INTEGER,      -- FK to product_hierarchy.product_id
    store_code VARCHAR,        -- FK to location.location
    transaction_date DATE,     -- FK to calendar.end_date
    sales_units INTEGER,       -- Units sold
    total_amount NUMERIC       -- Revenue per unit
)
-- IMPORTANT: Revenue = SUM(sales_units * total_amount)
""",
            
            # Key columns explanation
            "key_columns": {
                "sales_units": "Number of units sold (INTEGER)",
                "total_amount": "Revenue per unit (NUMERIC) - multiply by sales_units for total",
                "transaction_date": "Date of sale (DATE) - joins with calendar.end_date",
                "product_code": "Product ID (INTEGER) - joins with product_hierarchy.product_id",
                "store_code": "Store ID (VARCHAR) - joins with location.location"
            },
            
            # Required joins for sales queries
            "join_patterns": """
-- Standard Sales Joins:
FROM sales s
JOIN product_hierarchy ph ON s.product_code = ph.product_id
JOIN location l ON s.store_code = l.location
JOIN calendar c ON s.transaction_date = c.end_date
""",
            
            # Formulas to include
            "formulas": [],
            
            # Time context
            "time_context": self._detect_time_context(query_lower),
            
            # Aggregation hints
            "aggregation_hints": []
        }
        
        # Add relevant formulas based on query intent
        if any(word in query_lower for word in ["revenue", "total sales", "gross", "amount"]):
            hints["formulas"].append({
                "name": "Total Revenue",
                "sql": "SUM(s.sales_units * s.total_amount) AS revenue",
                "description": "Total revenue from sales transactions"
            })
            hints["aggregation_hints"].append("GROUP BY for dimensional analysis")
        
        if any(word in query_lower for word in ["units", "quantity", "how many sold", "volume"]):
            hints["formulas"].append({
                "name": "Total Units Sold",
                "sql": "SUM(s.sales_units) AS total_units",
                "description": "Total units sold"
            })
        
        if any(word in query_lower for word in ["week-on-week", "wow", "growth", "change"]):
            hints["formulas"].append({
                "name": "Week-on-Week % Change",
                "sql": "ROUND(((curr.units - prev.units)::NUMERIC / NULLIF(prev.units, 0)) * 100, 2) AS wow_change_pct",
                "description": "Percentage change from previous week to current week",
                "requires_cte": True,
                "cte_template": """
WITH current_week AS (
    SELECT {dimensions}, SUM(s.sales_units) AS units
    FROM sales s
    JOIN location l ON s.store_code = l.location
    WHERE s.transaction_date = '2025-11-08'
    GROUP BY {dimensions}
),
previous_week AS (
    SELECT {dimensions}, SUM(s.sales_units) AS units  
    FROM sales s
    JOIN location l ON s.store_code = l.location
    WHERE s.transaction_date = '2025-11-01'
    GROUP BY {dimensions}
)
SELECT curr.*, prev.units AS prev_units,
       ROUND(((curr.units - prev.units)::NUMERIC / NULLIF(prev.units, 0)) * 100, 2) AS wow_change_pct
FROM current_week curr
JOIN previous_week prev ON curr.{dimension} = prev.{dimension}
"""
            })
        
        if any(word in query_lower for word in ["velocity", "daily rate", "selling speed"]):
            hints["formulas"].append({
                "name": "Daily Sales Velocity",
                "sql": "SUM(s.sales_units) / 28.0 AS daily_velocity",
                "description": "Average daily sales over last 28 days",
                "filter": "WHERE s.transaction_date >= '2025-11-08'::date - INTERVAL '28 days'"
            })
        
        if any(word in query_lower for word in ["uplift", "above average", "spike", "above normal"]):
            hints["formulas"].append({
                "name": "Sales Uplift vs 4-Week Average",
                "sql": "curr_sales - avg_4week_sales AS sales_uplift",
                "description": "Current week sales minus 4-week average",
                "requires_cte": True
            })
        
        if any(word in query_lower for word in ["top", "highest", "best", "rank"]):
            hints["aggregation_hints"].append("ORDER BY revenue DESC LIMIT 10")
        
        if any(word in query_lower for word in ["bottom", "lowest", "worst"]):
            hints["aggregation_hints"].append("ORDER BY revenue ASC LIMIT 10")
        
        logger.info(f"📊 SalesAgent provided {len(hints['formulas'])} formula hints")
        return hints
    
    def _detect_time_context(self, query: str) -> Dict[str, Any]:
        """Detect time context from query"""
        # Static dates for demo data (Nov 8, 2025 is current)
        context = {
            "type": "current",
            "current_week_end": "2025-11-08",
            "previous_week_end": "2025-11-01",
            "next_week_end": "2025-11-15",
            "date_filter": None
        }
        
        if any(word in query for word in ["last week", "previous week"]):
            context["type"] = "historical"
            context["date_filter"] = "s.transaction_date = '2025-11-01'"
        elif any(word in query for word in ["this week", "current week"]):
            context["type"] = "current"
            context["date_filter"] = "s.transaction_date = '2025-11-08'"
        elif any(word in query for word in ["week-on-week", "compare", "vs"]):
            context["type"] = "comparison"
            context["date_filter"] = "s.transaction_date IN ('2025-11-01', '2025-11-08')"
        elif any(word in query for word in ["last month", "october"]):
            context["type"] = "historical"
            context["date_filter"] = "c.month = 'October' AND c.year = 2025"
        elif any(word in query for word in ["last 28 days", "last 4 weeks"]):
            context["type"] = "rolling"
            context["date_filter"] = "s.transaction_date >= '2025-11-08'::date - INTERVAL '28 days'"
        
        return context
    
    def get_example_queries(self) -> List[str]:
        """Return example queries this agent can help with"""
        return [
            "What were total sales last week?",
            "Show me revenue by region",
            "Which products are top sellers?",
            "What's the week-on-week sales change by region?",
            "Show sales performance for Ice Cream in Florida",
            "Calculate daily sales velocity for perishables",
            "Which region has highest sales growth?"
        ]


# Global instance
sales_agent = SalesAgent()
