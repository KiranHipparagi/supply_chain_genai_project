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
    - metrics (primary) - WDD trend data
    - product_hierarchy (joins by product name)
    - location (joins by location)
    - calendar (joins by end_date)
    - weekly_weather (optional for weather flags)
    
    CRITICAL CONCEPT:
    - metrics table contains DEMAND TRENDS, not actual sales
    - metric = Weather-Driven Demand prediction
    - metric_nrm = Normal demand (no weather impact) - use for FUTURE
    - metric_ly = Last Year demand - use for PAST/YoY comparisons
    """
    
    # Domain keywords
    WDD_KEYWORDS = [
        "wdd", "weather-driven demand", "weather driven demand",
        "demand forecast", "forecast demand", "expected demand",
        "weather impact on demand", "weather affect demand",
        "metric", "metric_nrm", "metric_ly",
        "adjusted demand", "adjusted velocity",
        "demand trend", "demand change", "demand uplift",
        "weather impact", "weather effect"
    ]
    
    # Combined context (weather + demand)
    WEATHER_DEMAND_COMBO = {
        "weather_words": ["weather", "heatwave", "cold spell", "rain", "temperature"],
        "demand_words": ["demand", "forecast", "expect", "impact", "uplift", "trend"]
    }
    
    # Exclude actual sales queries
    EXCLUDE_KEYWORDS = [
        "revenue", "sold units", "sales amount", "total amount",
        "how much sold", "units sold", "sales transaction", "actual sales"
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
            "description": "Weather-Driven Demand (WDD) analysis - demand TRENDS, not actual sales",
            
            # Table schema hints
            "table_schema": """
-- METRICS TABLE (WDD Demand Trends - NOT actual sales!)
metrics (
    product VARCHAR,           -- Product name (joins with product_hierarchy.product)
    location VARCHAR,          -- Store ID (joins with location.location)
    end_date DATE,             -- Week ending date (joins with calendar.end_date)
    metric NUMERIC,            -- Weather-Driven Demand prediction
    metric_nrm NUMERIC,        -- Normal demand (baseline, no weather) - USE FOR FUTURE
    metric_ly NUMERIC          -- Last Year demand - USE FOR PAST/YoY
)

-- CRITICAL: This is DIFFERENT from sales table!
-- metrics = demand TRENDS for forecasting
-- sales = actual TRANSACTIONS for reporting
""",
            
            # Key columns
            "key_columns": {
                "metric": "WDD prediction (weather-adjusted demand)",
                "metric_nrm": "Normal demand baseline (use for FUTURE/short-term ≤4 weeks)",
                "metric_ly": "Last Year demand (use for PAST/YoY/long-term >4 weeks)",
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
