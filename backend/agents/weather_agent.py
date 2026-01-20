"""
Weather Agent - Domain Expert for Weather Data Analysis
Provides domain hints for weather conditions, flags, and correlations.
Does NOT execute SQL - that's DatabaseAgent's job.
"""

from typing import Dict, Any, List
from core.logger import logger


class WeatherAgent:
    """
    Domain Expert for Weather Data Analysis.
    
    Responsibilities:
    - Identify if query is weather-related
    - Provide domain hints (weather columns, flags, temperature ranges)
    - Help correlate weather with sales/demand
    
    Does NOT:
    - Execute SQL queries
    - Connect to database directly
    
    Tables this expert knows about:
    - weekly_weather (primary)
    - location (joins)
    - calendar (joins)
    """
    
    WEATHER_KEYWORDS = [
        "weather", "temperature", "rain", "precipitation", "climate",
        "hot", "cold", "heatwave", "cold spell", "storm", "snow",
        "humid", "dry", "forecast", "tmax", "tmin",
        "weather condition", "weather impact", "weather flag"
    ]
    
    def __init__(self):
        logger.info("🌤️ WeatherAgent initialized as domain expert")
    
    def can_handle(self, query: str) -> bool:
        """Check if this agent can provide domain hints for the query"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.WEATHER_KEYWORDS)
    
    def get_domain_hints(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return domain-specific hints for SQL generation.
        This does NOT execute SQL - it provides context for DatabaseAgent.
        """
        query_lower = query.lower()
        
        hints = {
            "agent": "weather",
            "domain": "weather_analysis",
            "primary_table": "weekly_weather",
            "description": "Weather conditions and flags for demand correlation",
            
            # Table schema
            "table_schema": """
-- WEEKLY_WEATHER TABLE
weekly_weather (
    store_id VARCHAR,           -- Store ID (joins with location.location)
    week_end_date DATE,         -- Week ending date (joins with calendar.end_date)
    tmax NUMERIC,               -- Maximum temperature (°F)
    tmin NUMERIC,               -- Minimum temperature (°F)
    precip NUMERIC,             -- Precipitation (inches)
    heatwave_flag BOOLEAN,      -- True if heatwave conditions
    cold_spell_flag BOOLEAN,    -- True if cold spell conditions
    heavy_rain_flag BOOLEAN,    -- True if heavy rain
    snow_flag BOOLEAN           -- True if snow
)
""",
            
            # Key columns
            "key_columns": {
                "store_id": "Store ID (VARCHAR) - joins with location.location",
                "week_end_date": "Week ending date (DATE) - joins with calendar.end_date",
                "tmax": "Max temperature in °F",
                "tmin": "Min temperature in °F",
                "precip": "Precipitation in inches",
                "heatwave_flag": "Boolean - extreme heat conditions",
                "cold_spell_flag": "Boolean - extreme cold conditions",
                "heavy_rain_flag": "Boolean - heavy precipitation",
                "snow_flag": "Boolean - snow conditions"
            },
            
            # Join patterns
            "join_patterns": """
-- Standard Weather Joins:
FROM weekly_weather w
JOIN location l ON w.store_id = l.location
JOIN calendar c ON w.week_end_date = c.end_date
""",
            
            # Weather flag formulas
            "formulas": [],
            
            # Weather condition definitions
            "weather_definitions": {
                "ideal_beach_weather": "tmax BETWEEN 80 AND 95 AND tmin >= 65 AND precip <= 0.1 AND heatwave_flag = false AND cold_spell_flag = false AND heavy_rain_flag = false",
                "heatwave": "heatwave_flag = true OR tmax > 95",
                "cold_spell": "cold_spell_flag = true OR tmin < 32",
                "rainy": "heavy_rain_flag = true OR precip > 0.5",
                "normal": "heatwave_flag = false AND cold_spell_flag = false AND heavy_rain_flag = false AND snow_flag = false"
            },
            
            # Time context
            "time_context": self._detect_time_context(query_lower)
        }
        
        # Add weather condition formula
        if any(word in query_lower for word in ["condition", "flag", "type of weather"]):
            hints["formulas"].append({
                "name": "Weather Condition Classification",
                "sql": """
CASE 
    WHEN w.heatwave_flag = true THEN 'Heatwave'
    WHEN w.cold_spell_flag = true THEN 'Cold Spell'
    WHEN w.heavy_rain_flag = true THEN 'Heavy Rain'
    WHEN w.snow_flag = true THEN 'Snow'
    ELSE 'Normal'
END AS weather_condition
""",
                "description": "Classify weather into conditions"
            })
        
        # Temperature analysis
        if any(word in query_lower for word in ["temperature", "hot", "cold", "tmax", "tmin"]):
            hints["formulas"].append({
                "name": "Temperature Stats",
                "sql": "AVG(w.tmax) AS avg_high_temp, AVG(w.tmin) AS avg_low_temp, MAX(w.tmax) AS max_temp, MIN(w.tmin) AS min_temp",
                "description": "Temperature statistics"
            })
        
        # Precipitation analysis
        if any(word in query_lower for word in ["rain", "precipitation", "precip", "wet"]):
            hints["formulas"].append({
                "name": "Precipitation Stats",
                "sql": "SUM(w.precip) AS total_precip, AVG(w.precip) AS avg_precip",
                "description": "Precipitation totals and averages"
            })
        
        # Weather event counts
        if any(word in query_lower for word in ["how many", "count", "events", "occurrences"]):
            hints["formulas"].append({
                "name": "Weather Event Counts",
                "sql": """
SUM(CASE WHEN w.heatwave_flag THEN 1 ELSE 0 END) AS heatwave_count,
SUM(CASE WHEN w.cold_spell_flag THEN 1 ELSE 0 END) AS cold_spell_count,
SUM(CASE WHEN w.heavy_rain_flag THEN 1 ELSE 0 END) AS heavy_rain_count,
SUM(CASE WHEN w.snow_flag THEN 1 ELSE 0 END) AS snow_count
""",
                "description": "Count of weather events"
            })
        
        # Beach weather (for food diversification queries)
        if any(word in query_lower for word in ["beach", "ideal", "miami", "coastal", "summer", "weekend"]):
            hints["formulas"].append({
                "name": "Ideal Beach Weather Filter",
                "sql": "w.tmax BETWEEN 80 AND 95 AND w.tmin >= 65 AND w.precip <= 0.1 AND w.heatwave_flag = false AND w.cold_spell_flag = false AND w.heavy_rain_flag = false AND w.snow_flag = false",
                "description": "Filter for ideal beach weather conditions (80-95°F, ≤0.1\" rain, no adverse flags)",
                "use_as": "WHERE clause condition"
            })
            
            # Weekend-specific filtering (Saturday = DOW 6)
            if "weekend" in query_lower or "saturday" in query_lower:
                hints["formulas"].append({
                    "name": "Weekend Filter (Saturday)",
                    "sql": "EXTRACT(DOW FROM c.end_date) = 6",
                    "description": "Filter for Saturday week-ending dates (DOW = 6 for Saturday)",
                    "use_as": "WHERE clause - ensures only weekend dates are selected"
                })
        
        logger.info(f"🌤️ WeatherAgent provided {len(hints['formulas'])} weather hints")
        return hints
    
    def _detect_time_context(self, query: str) -> Dict[str, Any]:
        """Detect time context from query"""
        context = {
            "current_week_end": "2025-11-08",
            "date_filter": None
        }
        
        if any(word in query for word in ["last week", "previous week"]):
            context["date_filter"] = "w.week_end_date = '2025-11-01'"
        elif any(word in query for word in ["next week"]):
            context["date_filter"] = "w.week_end_date = '2025-11-15'"
        elif any(word in query for word in ["this week", "current"]):
            context["date_filter"] = "w.week_end_date = '2025-11-08'"
        elif any(word in query for word in ["last year", "2024"]):
            context["date_filter"] = "c.year = 2024"
        
        return context
    
    def get_example_queries(self) -> List[str]:
        """Return example queries this agent can help with"""
        return [
            "What was the weather last week in Florida?",
            "Show stores with heatwave conditions",
            "How many cold spell events in Northeast?",
            "What's the average temperature by region?",
            "Find weeks with ideal beach weather in Miami"
        ]


# Global instance
weather_agent = WeatherAgent()
