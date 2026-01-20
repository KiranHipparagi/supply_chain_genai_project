"""
Events Agent - Domain Expert for Event Analysis
Provides domain hints for events, holidays, and their impact on demand.
Does NOT execute SQL - that's DatabaseAgent's job.
"""

from typing import Dict, Any, List
from core.logger import logger


class EventsAgent:
    """
    Domain Expert for Event Analysis.
    
    Responsibilities:
    - Identify if query is events-related
    - Provide domain hints (event types, proximity, impact)
    - Help correlate events with demand spikes
    
    Does NOT:
    - Execute SQL queries
    - Connect to database directly
    
    Tables this expert knows about:
    - events (primary)
    - location (joins)
    - calendar (joins)
    """
    
    EVENTS_KEYWORDS = [
        "event", "events", "holiday", "festival", "concert",
        "sports", "game", "match", "thanksgiving", "christmas",
        "super bowl", "memorial day", "labor day", "black friday",
        "new year", "easter", "halloween", "fourth of july",
        "event impact", "event proximity", "upcoming event"
    ]
    
    # Event types
    EVENT_TYPES = [
        "Sports", "Concert", "Festival", "Holiday", "Conference",
        "Fair", "Convention", "Parade", "Marathon", "Cultural"
    ]
    
    def __init__(self):
        logger.info("🎉 EventsAgent initialized as domain expert")
    
    def can_handle(self, query: str) -> bool:
        """Check if this agent can provide domain hints for the query"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.EVENTS_KEYWORDS)
    
    def get_domain_hints(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return domain-specific hints for SQL generation.
        This does NOT execute SQL - it provides context for DatabaseAgent.
        """
        query_lower = query.lower()
        
        hints = {
            "agent": "events",
            "domain": "event_analysis",
            "primary_table": "events",
            "description": "Event data including holidays, sports, festivals mapped to store proximity",
            
            # Table schema
            "table_schema": """
-- EVENTS TABLE
events (
    event VARCHAR,              -- Event name
    event_type VARCHAR,         -- Type: Sports, Concert, Festival, Holiday, etc.
    event_date DATE,            -- Date of event
    store_id VARCHAR,           -- Store in proximity (joins with location.location)
    event_start_date DATE,      -- Multi-day event start
    event_end_date DATE         -- Multi-day event end
)
-- Events are pre-mapped to stores by geographic proximity (lat/long)
""",
            
            # Key columns
            "key_columns": {
                "event": "Event name (VARCHAR)",
                "event_type": "Event category: Sports, Concert, Festival, Holiday, etc.",
                "event_date": "Primary event date (DATE)",
                "store_id": "Store ID in proximity (joins with location.location)",
                "event_start_date": "Multi-day event start (DATE)",
                "event_end_date": "Multi-day event end (DATE)"
            },
            
            # Join patterns
            "join_patterns": """
-- Standard Events Joins:
FROM events e
JOIN location l ON e.store_id = l.location
-- To correlate with calendar:
JOIN calendar c ON e.event_date = c.end_date
""",
            
            # Event types list
            "event_types": self.EVENT_TYPES,
            
            # Formulas
            "formulas": [],
            
            # Time context
            "time_context": self._detect_time_context(query_lower)
        }
        
        # Event counts
        if any(word in query_lower for word in ["how many", "count", "number of"]):
            hints["formulas"].append({
                "name": "Event Count",
                "sql": "COUNT(DISTINCT e.event) AS event_count",
                "description": "Count of distinct events"
            })
        
        # Events by type
        if any(word in query_lower for word in ["type", "category", "breakdown"]):
            hints["formulas"].append({
                "name": "Events by Type",
                "sql": "e.event_type, COUNT(*) AS event_count",
                "description": "Events grouped by type",
                "requires_groupby": "GROUP BY e.event_type"
            })
        
        # Upcoming events
        if any(word in query_lower for word in ["upcoming", "next", "future", "scheduled"]):
            hints["formulas"].append({
                "name": "Upcoming Events Filter",
                "sql": "e.event_date >= '2025-11-08'",
                "description": "Filter for future events",
                "use_as": "WHERE clause"
            })
        
        # Events by region
        if any(word in query_lower for word in ["region", "by region", "regional"]):
            hints["formulas"].append({
                "name": "Events by Region",
                "sql": "l.region, COUNT(DISTINCT e.event) AS event_count",
                "description": "Events grouped by region",
                "requires_groupby": "GROUP BY l.region"
            })
        
        # High-impact events
        if any(word in query_lower for word in ["major", "big", "important", "high impact"]):
            hints["formulas"].append({
                "name": "Major Events Filter",
                "sql": "e.event_type IN ('Holiday', 'Sports', 'Festival')",
                "description": "Filter for high-impact event types",
                "use_as": "WHERE clause"
            })
        
        # Holiday specific
        if any(word in query_lower for word in ["holiday", "thanksgiving", "christmas", "easter"]):
            hints["formulas"].append({
                "name": "Holiday Events Filter",
                "sql": "e.event_type = 'Holiday'",
                "description": "Filter for holiday events only",
                "use_as": "WHERE clause"
            })
        
        # Event proximity checking (for "no events" queries)
        if any(word in query_lower for word in ["no event", "without event", "no scheduled event", "proximity"]):
            hints["formulas"].append({
                "name": "Event Proximity Check (7-day window)",
                "sql": """LEFT JOIN events e ON l.market = e.market 
  AND e.event_date BETWEEN c.end_date - INTERVAL '7 days' AND c.end_date""",
                "description": "Check for events within 7 days of the week ending date",
                "use_as": "JOIN clause",
                "filter_no_events": "HAVING COUNT(e.event) = 0"
            })
            
            hints["formulas"].append({
                "name": "No Events Filter",
                "sql": "COUNT(e.event) = 0",
                "description": "Filter for weeks with NO events in proximity",
                "use_as": "HAVING clause after GROUP BY"
            })
        
        # Event impact (correlation with sales spikes)
        if any(word in query_lower for word in ["impact", "correlation", "rise", "spike", "increase"]):
            hints["formulas"].append({
                "name": "Event Impact Analysis",
                "sql": "COUNT(DISTINCT e.event) AS nearby_events, STRING_AGG(DISTINCT e.event, ', ') AS event_names",
                "description": "Count and list events near the analysis period",
                "requires_groupby": True
            })
        
        logger.info(f"🎉 EventsAgent provided {len(hints['formulas'])} event hints")
        return hints
    
    def _detect_time_context(self, query: str) -> Dict[str, Any]:
        """Detect time context from query"""
        context = {
            "current_date": "2025-11-08",
            "date_filter": None,
            "timeframe": "current"
        }
        
        if any(word in query for word in ["upcoming", "next", "future"]):
            context["timeframe"] = "future"
            context["date_filter"] = "e.event_date >= '2025-11-08'"
        elif any(word in query for word in ["past", "previous", "last"]):
            context["timeframe"] = "past"
            context["date_filter"] = "e.event_date < '2025-11-08'"
        elif any(word in query for word in ["this month", "november"]):
            context["timeframe"] = "current_month"
            context["date_filter"] = "e.event_date BETWEEN '2025-11-01' AND '2025-11-30'"
        elif any(word in query for word in ["next month", "december"]):
            context["timeframe"] = "next_month"
            context["date_filter"] = "e.event_date BETWEEN '2025-12-01' AND '2025-12-31'"
        
        return context
    
    def get_example_queries(self) -> List[str]:
        """Return example queries this agent can help with"""
        return [
            "What events are happening next month?",
            "Show me holiday events in the South region",
            "How many sports events are near Miami stores?",
            "What's the event breakdown by type?",
            "List upcoming festivals in the Northeast"
        ]


# Global instance
events_agent = EventsAgent()
