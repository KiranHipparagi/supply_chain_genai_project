"""
Metrics Agent (WDD Agent) - Domain Expert for Weather-Driven Demand Analysis
Provides domain hints for WDD calculations, demand forecasting, weather impact trends.
Does NOT execute SQL - that's DatabaseAgent's job.
"""

from typing import Dict, Any, List
from core.logger import logger


class MetricsAgent:
    """
    Domain Expert for Weather-Driven Demand (WDD) Analysis.
    
    Responsibilities:
    - Identify if query is WDD/metrics-related
    - Provide domain hints (columns, formulas, time context rules)
    - Distinguish between FUTURE queries (use metric_nrm) and PAST queries (use metric_ly)
    
    Does NOT:
    - Execute SQL queries
    - Connect to database directly
    
    Tables this expert knows about:
    - metrics (primary) - WDD TREND data (NOT actual demand numbers!)
    - product_hierarchy (joins by product name)
    - location (joins by location)
    - calendar (joins by end_date)
    - sales (for actual sales to calculate recommended orders)
    - weekly_weather (optional for weather flags)
    
    CRITICAL CONCEPT - METRICS TABLE EXPLAINED:
    ===========================================
    The metrics table contains WEEKLY WDD TREND DATA for analyzing 
    spikes or dips in demand due to WEATHER ONLY.
    
    These metric numbers are NOT actual demand numbers - they are 
    TREND VALUES used to see weather-driven patterns.
    
    - metric = Weather-Driven Demand (WDD) trend value
    - metric_nrm = Normal demand trend (baseline, no weather impact)
    - metric_ly = Last Year demand trend
    
    WDD FORMULA SELECTION RULES:
    - Short-term (≤4 weeks, FUTURE): Use metric vs metric_nrm
      Formula: (SUM(metric) - SUM(metric_nrm)) / NULLIF(SUM(metric_nrm), 0) * 100
      
    - Long-term (>4 weeks) OR Historical/YoY: Use metric vs metric_ly
      Formula: (SUM(metric) - SUM(metric_ly)) / NULLIF(SUM(metric_ly), 0) * 100
    
    RECOMMENDED ORDER FORMULA (CRITICAL!):
    =====================================
    Adjusted Qty = Last-week sales × (1 + WDD %)
    
    This uses ACTUAL sales from sales table multiplied by WDD percentage
    to recommend ordering volume for the coming week.
    """
    
    # Domain keywords
    WDD_KEYWORDS = [
        "wdd", "weather-driven demand", "weather driven demand",
        "demand forecast", "forecast demand", "expected demand",
        "weather impact on demand", "weather affect demand",
        "metric", "metric_nrm", "metric_ly",
        "adjusted demand", "adjusted velocity", "adjusted qty",
        "demand trend", "demand change", "demand uplift",
        "weather impact", "weather effect",
        "recommended order", "ordering volume", "procurement", "reorder",
        # Restaurant sector queries
        "restaurant traffic", "restaurant sector", "restaurant performance",
        # Add patterns that indicate WDD analysis
        "below-normal demand", "above-normal demand", "normal demand",
        "higher-than-normal", "lower-than-normal",
        "demand next week", "demand next month", "demand last week",
        "demand vs normal", "demand vs last year",
        "weather-driven", "weather pattern",
        # Year-over-year WDD patterns
        "year-over-year", "yoy", "vs last year", "vs ly",
        "best performance", "strongest performance", "highest performance"
    ]
    
    # Combined context (weather + demand)
    WEATHER_DEMAND_COMBO = {
        "weather_words": ["weather", "heatwave", "cold spell", "rain", "temperature", "forecast", "pattern", "based on"],
        "demand_words": ["demand", "forecast", "expect", "impact", "uplift", "trend", "order", "ordering", "normal", "performance"]
    }
    
    # Exclude actual sales queries
    EXCLUDE_KEYWORDS = [
        "revenue only", "sold units only", "sales amount only",
        "how much sold", "units sold count"
    ]
    
    def __init__(self):
        logger.info("📈 MetricsAgent initialized as domain expert (WDD)")
    
    def can_handle(self, query: str) -> bool:
        """Check if this agent can provide domain hints for the query"""
        query_lower = query.lower()
        
        # Direct WDD keywords
        has_wdd_keyword = any(kw in query_lower for kw in self.WDD_KEYWORDS)
        
        # Weather + demand combination
        has_weather = any(w in query_lower for w in self.WEATHER_DEMAND_COMBO["weather_words"])
        has_demand = any(w in query_lower for w in self.WEATHER_DEMAND_COMBO["demand_words"])
        weather_demand_combo = has_weather and has_demand
        
        # Exclude actual sales
        has_exclude = any(kw in query_lower for kw in self.EXCLUDE_KEYWORDS)
        
        return (has_wdd_keyword or weather_demand_combo) and not has_exclude
    
    def get_domain_hints(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return domain-specific hints for SQL generation.
        This does NOT execute SQL - it provides context for DatabaseAgent.
        """
        query_lower = query.lower()
        time_context = self._detect_time_context(query_lower)
        
        hints = {
            "agent": "metrics",
            "domain": "weather_driven_demand",
            "primary_table": "metrics",
            "description": "Weather-Driven Demand (WDD) TREND analysis - NOT actual sales numbers!",
            
            # Table schema hints
            "table_schema": """
-- METRICS TABLE (WDD Demand TRENDS - NOT actual sales numbers!)
-- These are TREND VALUES for weather impact analysis, not real demand
metrics (
    product VARCHAR,           -- Product name (joins with product_hierarchy.product)
    location VARCHAR,          -- Store ID (joins with location.location)
    end_date DATE,             -- Week ending date (joins with calendar.end_date)
    metric NUMERIC,            -- WDD trend value (weather-adjusted)
    metric_nrm NUMERIC,        -- Normal demand trend (baseline) - USE FOR SHORT-TERM FUTURE ≤4 weeks
    metric_ly NUMERIC          -- Last Year demand trend - USE FOR LONG-TERM >4 weeks OR Historical/YoY
)

-- CRITICAL UNDERSTANDING:
-- metric numbers are NOT actual demand - they're TREND VALUES
-- Use metrics table to calculate WDD PERCENTAGE, then apply to actual sales

-- WDD FORMULA SELECTION:
-- Short-term (≤4 weeks, FUTURE): (SUM(metric) - SUM(metric_nrm)) / NULLIF(SUM(metric_nrm), 0) * 100
-- Long-term (>4 weeks) OR Historical: (SUM(metric) - SUM(metric_ly)) / NULLIF(SUM(metric_ly), 0) * 100
""",
            
            # Key columns
            "key_columns": {
                "metric": "WDD trend value (NOT actual demand)",
                "metric_nrm": "Normal demand trend (use for FUTURE ≤4 weeks)",
                "metric_ly": "Last Year demand trend (use for PAST/YoY/>4 weeks)",
                "product": "Product name (VARCHAR) - joins with product_hierarchy.product",
                "location": "Store ID (VARCHAR) - joins with location.location",
                "end_date": "Week ending date (DATE) - joins with calendar.end_date"
            },
            
            # Join patterns
            "join_patterns": """
-- Standard Metrics Joins (NOTE: joins on product NAME, not ID!):
FROM metrics m
JOIN product_hierarchy ph ON m.product = ph.product
JOIN location l ON m.location = l.location
JOIN calendar c ON m.end_date = c.end_date
-- Optional weather join:
LEFT JOIN weekly_weather w ON m.location = w.store_id AND m.end_date = w.week_end_date
""",
            
            # Time context is CRITICAL for WDD
            "time_context": time_context,
            
            # Formulas
            "formulas": [],
            
            # Important notes
            "critical_notes": [
                "metrics.product is VARCHAR name, NOT integer ID",
                "Join with product_hierarchy ON product NAME",
                "FUTURE queries (≤4 weeks): use metric vs metric_nrm",
                "PAST queries (>4 weeks, YoY): use metric vs metric_ly"
            ]
        }
        
        # CRITICAL: Seasonal Planning Query Guidance (Q6, Q7, Q8, Q9)
        if any(word in query_lower for word in ["spring", "summer", "fall", "winter", "season", "seasonal"]):
            hints["seasonal_guidance"] = {
                "critical_rules": [
                    "❌ NEVER filter c.year IN (2024, 2025) - causes double-counting!",
                    "✅ Filter ONE year only (usually current year for historical, next year for future)",
                    "✅ metric = current year data, metric_ly = last year data AUTOMATICALLY",
                    "✅ 'last spring' = Spring 2025 (historical), 'coming spring' = Spring 2026 (future)",
                    "✅ Historical queries: c.year = 2025 AND m.end_date <= '2025-11-08'",
                    "✅ Future queries: c.year = 2025 (Winter) or 2026 (Spring/Summer/Fall) AND m.end_date >= '2025-11-09'",
                    "✅ For risks: ORDER BY wdd_pct DESC (NOT ABS(alias) - PostgreSQL error!)",
                    "✅ If ABS needed: ORDER BY ABS((full_expression)) DESC - repeat calculation, don't use alias",
                    "❌ Never ORDER BY ASC for 'biggest risks' - that shows smallest!"
                ],
                "temporal_mapping": {
                    "last spring": "c.season = 'Spring' AND c.year = 2025 AND m.end_date <= '2025-11-08'",
                    "coming spring": "c.season = 'Spring' AND c.year = 2026 AND m.end_date >= '2025-11-09'",
                    "last summer": "c.season = 'Summer' AND c.year = 2025 AND m.end_date <= '2025-11-08'",
                    "coming winter": "c.season = 'Winter' AND c.year = 2025 AND m.end_date >= '2025-11-09'",
                    "past summer": "c.season = 'Summer' AND c.year = 2025 AND m.end_date <= '2025-11-08'",
                    "prior summer": "Use metric vs metric_ly, filter c.year = 2025"
                },
                "product_hierarchy_note": "Use ph.dept for 'Apparel sector', ph.category for subcategories, ph.product for items",
                "grouping_note": "Do NOT group by c.month unless explicitly asked - group by season or region"
            }
        
        # CRITICAL: Restaurant Sector Queries (Q10)
        if any(word in query_lower for word in ["restaurant", "qsr"]):
            hints["restaurant_guidance"] = {
                "sector_filter": "ph.product = 'Restaurant Sector' (NOT ph.category = 'QSR'!)",
                "critical_note": "'Restaurant Sector' is a special PRODUCT-level entry for sector analysis (no parent hierarchy)",
                "categories_within": ["QSR", "Fast Food", "Casual Dining"],
                "example": "WHERE ph.product = 'Restaurant Sector' captures ALL restaurant categories"
            }
        
        # Add WDD formula based on time context
        if time_context["comparison_type"] == "future":
            hints["formulas"].append({
                "name": "WDD vs Normal (Future)",
                "sql": "(SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) * 100 AS wdd_vs_normal_pct",
                "description": "Weather impact on demand vs normal baseline (for future predictions)",
                "when_to_use": "FUTURE queries, short-term ≤4 weeks"
            })
        else:
            hints["formulas"].append({
                "name": "WDD vs Last Year (Past)",
                "sql": "(SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100 AS wdd_vs_ly_pct",
                "description": "Weather impact on demand vs last year (for historical analysis)",
                "when_to_use": "PAST queries, YoY comparisons, >4 weeks"
            })
        
        # Adjusted velocity formula
        if any(word in query_lower for word in ["adjusted velocity", "weather-adjusted", "forecast velocity"]):
            hints["formulas"].append({
                "name": "Adjusted Velocity",
                "sql": "daily_velocity * (1 + wdd_pct / 100) AS adjusted_velocity",
                "description": "Daily Sales Velocity × (1 + WDD%)",
                "requires_cte": True,
                "cte_hint": "First calculate daily_velocity from sales, then join with WDD from metrics"
            })
        
        # Adjusted demand formula
        if any(word in query_lower for word in ["adjusted demand", "weather-adjusted demand", "forecast demand"]):
            hints["formulas"].append({
                "name": "Adjusted Demand",
                "sql": "avg_4week_sales * (1 + wdd_pct / 100) AS adjusted_demand",
                "description": "Avg 4-Week Sales × (1 + WDD%)",
                "requires_cte": True,
                "cte_hint": "First calculate avg_4week_sales from sales, then join with WDD from metrics"
            })
        
        # CRITICAL: Recommended Order / Adjusted Qty formula
        # This is the testing team's official formula for Q5 and similar queries
        if any(word in query_lower for word in ["recommend", "order", "reorder", "procurement", "adjusted qty", "ordering volume", "should order", "how much to order", "prevent waste", "adjust ordering", "next seven days", "next week", "coming week"]):
            hints["formulas"].append({
                "name": "Recommended Order / Adjusted Qty (Q5 Type)",
                "sql": """
-- ⚠️ CRITICAL: Use ACTUAL sales from sales table, NOT metric_ly!
-- STEP 1: Get last week's ACTUAL sales from sales table
WITH last_week_sales AS (
    SELECT ph.product, l.region, l.market,
           SUM(s.sales_units) AS last_week_units
    FROM sales s
    JOIN product_hierarchy ph ON s.product_code = ph.product_id
    JOIN location l ON s.store_code = l.location
    WHERE s.transaction_date BETWEEN '2025-11-02' AND '2025-11-08'  -- Last week
    GROUP BY ph.product, l.region, l.market
),
-- STEP 2: Get WDD percentage from metrics table for NEXT week
wdd_forecast AS (
    SELECT ph.product, l.region, l.market,
           (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) AS wdd_pct
    FROM metrics m
    JOIN product_hierarchy ph ON m.product = ph.product
    JOIN location l ON m.location = l.location
    WHERE m.end_date = '2025-11-15'  -- Next week
    GROUP BY ph.product, l.region, l.market
)
-- STEP 3: Apply formula: Last-week sales × (1 + WDD %)
SELECT 
    lws.product, lws.market, lws.region,
    lws.last_week_units AS last_week_sales,
    ROUND(wf.wdd_pct * 100, 2) AS wdd_change_pct,
    ROUND(lws.last_week_units * (1 + COALESCE(wf.wdd_pct, 0)), 0) AS recommended_order_qty,
    ROUND((lws.last_week_units * (1 + COALESCE(wf.wdd_pct, 0))) - lws.last_week_units, 0) AS qty_change_vs_last_week
FROM last_week_sales lws
LEFT JOIN wdd_forecast wf ON lws.product = wf.product AND lws.market = wf.market
WHERE lws.last_week_units > 0
ORDER BY recommended_order_qty DESC
""",
                "description": "Recommended Order Qty = Last-week sales × (1 + WDD %)",
                "critical_note": "❌ NEVER use metric_ly as baseline! ✅ ALWAYS use ACTUAL sales from sales table!",
                "formula": "Adjusted Qty = Last-week ACTUAL sales × (1 + WDD % vs Normal)",
                "baseline_source": "sales table (NOT metrics table)",
                "critical_for": "Q5 - Tampa perishable ordering volume"
            })
            
            # ADDITIONAL: Shelf Life Risk for "prevent waste" or "shrinkage" queries (Q3, Q4 type)
            if any(word in query_lower for word in ["prevent waste", "adjust ordering", "waste", "perishable", "expir", "shelf life", "shrinkage", "shrink", "increase display", "meet demand"]):
                hints["formulas"].append({
                    "name": "Shelf Life Risk + Daily Sales Velocity (Waste/Shrinkage Prevention)",
                    "sql": """
-- SHRINKAGE/WASTE RISK ANALYSIS with WDD Impact
-- CRITICAL: In PostgreSQL, date - date = INTEGER (days), NO need for EXTRACT(DAY FROM ...)
-- Daily Sales Velocity
WITH daily_velocity AS (
    SELECT ph.product, l.region,
           SUM(s.sales_units) / 28.0 AS daily_sales_velocity
    FROM sales s
    JOIN product_hierarchy ph ON s.product_code = ph.product_id
    JOIN location l ON s.store_code = l.location
    WHERE s.transaction_date >= '2025-10-12'  -- Last 28 days
    GROUP BY ph.product, l.region
),
-- Current Stock & Expiry Info
-- CRITICAL: p.max_period is TEXT, must cast to INTEGER for arithmetic!
current_inventory AS (
    SELECT ph.product, l.region,
           SUM(b.stock_at_week_end) AS current_stock,
           MAX(CAST(p.max_period AS INTEGER)) AS shelf_life_days,
           AVG('2025-11-08'::date - b.transfer_in_date) AS avg_age_days
    FROM batches b
    JOIN product_hierarchy ph ON b.product_code = ph.product_id
    JOIN location l ON b.store_code = l.location
    LEFT JOIN perishable p ON ph.product = p.product
    WHERE b.week_end_date = '2025-11-08'  -- Current week
    GROUP BY ph.product, l.region
),
-- WDD Impact for demand change
wdd_impact AS (
    SELECT ph.product, l.region,
           (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) * 100 AS expected_demand_change_pct
    FROM metrics m
    JOIN product_hierarchy ph ON m.product_code = ph.product_id
    JOIN location l ON m.store_code = l.location
    WHERE m.weather_date >= '2025-11-09' AND m.weather_date <= '2025-11-16'  -- Next week forecast
    GROUP BY ph.product, l.region
)
-- Calculate shrinkage/waste risk WITH WDD consideration
SELECT ci.product, ci.region,
       ci.current_stock,
       dv.daily_sales_velocity,
       ci.shelf_life_days,
       ROUND(ci.shelf_life_days - ci.avg_age_days) AS days_until_expiry,
       ROUND(wi.expected_demand_change_pct, 2) AS wdd_change_pct,
       ROUND(dv.daily_sales_velocity * 7 * (1 + COALESCE(wi.expected_demand_change_pct, 0) / 100), 0) AS projected_weekly_demand,
       CASE 
         WHEN ci.shelf_life_days - ci.avg_age_days > 0 THEN
           GREATEST(0, ci.current_stock - (dv.daily_sales_velocity * (ci.shelf_life_days - ci.avg_age_days)))
         ELSE ci.current_stock
       END AS potential_shrinkage_units,
       ROUND(CASE 
         WHEN ci.current_stock > 0 THEN
           GREATEST(0, ci.current_stock - (dv.daily_sales_velocity * (ci.shelf_life_days - ci.avg_age_days))) / ci.current_stock * 100
         ELSE 0
       END, 2) AS shrinkage_risk_pct
FROM current_inventory ci
JOIN daily_velocity dv ON ci.product = dv.product AND ci.region = dv.region
LEFT JOIN wdd_impact wi ON ci.product = wi.product AND ci.region = wi.region
WHERE ci.shelf_life_days IS NOT NULL
""",
                    "description": "Calculate shrinkage/waste risk with WDD impact for perishable items",
                    "requires_join": "batches b JOIN perishable p ON product, metrics m for WDD",
                    "critical_for": "Q3 (prevent waste) and Q4 (shrinkage risk) analysis"
                })
        
        # Weather flag correlation
        if any(word in query_lower for word in ["heatwave", "cold spell", "storm", "weather flag"]):
            hints["formulas"].append({
                "name": "WDD During Weather Events",
                "sql": """
CASE WHEN w.heatwave_flag THEN 'Heatwave'
     WHEN w.cold_spell_flag THEN 'Cold Spell'
     WHEN w.heavy_rain_flag THEN 'Heavy Rain'
     ELSE 'Normal' END AS weather_condition
""",
                "description": "Correlate WDD with weather flags",
                "requires_join": "LEFT JOIN weekly_weather w ON m.location = w.store_id AND m.end_date = w.week_end_date"
            })
        
        logger.info(f"📈 MetricsAgent provided {len(hints['formulas'])} formula hints (time_context: {time_context['comparison_type']})")
        return hints
    
    def _detect_time_context(self, query: str) -> Dict[str, Any]:
        """
        Detect time context - CRITICAL for choosing metric_nrm vs metric_ly.
        
        Rules:
        - FUTURE (≤4 weeks ahead): Use metric vs metric_nrm
        - PAST (historical, YoY, >4 weeks): Use metric vs metric_ly
        """
        # Static dates for demo (Nov 8, 2025 is current)
        context = {
            "comparison_type": "future",  # Default to future
            "current_week_end": "2025-11-08",
            "metric_comparison": "metric_nrm",  # Default
            "date_filter": None
        }
        
        # PAST indicators → use metric_ly
        past_indicators = [
            "last year", "ly", "year over year", "yoy", "historical",
            "last quarter", "last month", "past", "ago", "previous year"
        ]
        
        if any(indicator in query for indicator in past_indicators):
            context["comparison_type"] = "past"
            context["metric_comparison"] = "metric_ly"
            context["date_filter"] = "m.end_date <= '2025-11-08'"
        
        # FUTURE indicators → use metric_nrm
        future_indicators = [
            "next week", "next month", "upcoming", "forecast", "predict",
            "expected", "will be", "going to", "future"
        ]
        
        if any(indicator in query for indicator in future_indicators):
            context["comparison_type"] = "future"
            context["metric_comparison"] = "metric_nrm"
            context["date_filter"] = "m.end_date >= '2025-11-08'"
        
        return context
    
    def get_example_queries(self) -> List[str]:
        """Return example queries this agent can help with"""
        return [
            "What's the weather impact on ice cream demand next week?",
            "Show WDD vs normal for perishables",
            "Which products have highest weather-driven demand uplift?",
            "Compare demand trend vs last year",
            "What's the adjusted demand for milk during heatwave?",
            "Show weather-driven demand forecast for Florida"
        ]


# Global instance  
metrics_agent = MetricsAgent()
