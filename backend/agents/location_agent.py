"""
Location Agent - Domain Expert for Location/Geographic Analysis
Provides domain hints for regions, markets, states, and store-level data.
Does NOT execute SQL - that's DatabaseAgent's job.
"""

from typing import Dict, Any, List
from core.logger import logger


class LocationAgent:
    """
    Domain Expert for Location/Geographic Analysis.
    
    Responsibilities:
    - Identify if query is location-related
    - Provide domain hints (region/market/state hierarchy)
    - Support geographic filtering and aggregation
    
    Does NOT:
    - Execute SQL queries
    - Connect to database directly
    
    Tables this expert knows about:
    - location (primary)
    """
    
    LOCATION_KEYWORDS = [
        "location", "store", "region", "regional",
        "market", "state", "area", "geographic",
        "northeast", "southeast", "midwest", "southwest", "west",
        "florida", "texas", "california", "new york",
        "miami", "tampa", "boston", "chicago", "dallas", "san francisco", "los angeles",
        "by region", "by market", "by state", "by store"
    ]
    
    # Known regions (lowercase for matching)
    REGIONS = ["northeast", "southeast", "midwest", "southwest", "west", "south"]
    
    # Sample markets (include Tampa, San Francisco)
    MARKETS = ["miami, fl", "tampa, fl", "boston, ma", "chicago, il", "dallas, tx", "los angeles, ca", "san francisco, ca"]
    
    def __init__(self):
        logger.info("📍 LocationAgent initialized as domain expert")
    
    def can_handle(self, query: str) -> bool:
        """Check if this agent can provide domain hints for the query"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.LOCATION_KEYWORDS)
    
    def get_domain_hints(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Return domain-specific hints for SQL generation.
        This does NOT execute SQL - it provides context for DatabaseAgent.
        """
        query_lower = query.lower()
        
        hints = {
            "agent": "location",
            "domain": "geographic_analysis",
            "primary_table": "location",
            "description": "Geographic hierarchy and store location data",
            
            # Table schema
            "table_schema": """
-- LOCATION TABLE
location (
    id INTEGER,                 -- Primary key
    location VARCHAR,           -- Store ID (e.g., 'ST0050')
    region VARCHAR,             -- Region (e.g., 'northeast', 'southeast') - LOWERCASE
    market VARCHAR,             -- Market (e.g., 'Miami, FL', 'Boston, MA')
    state VARCHAR,              -- State (e.g., 'Florida', 'Massachusetts')
    latitude NUMERIC,           -- Geographic coordinates
    longitude NUMERIC           -- Geographic coordinates
)

-- IMPORTANT: region values are LOWERCASE (e.g., 'northeast' not 'Northeast')
""",
            
            # Key columns
            "key_columns": {
                "location": "Store ID (VARCHAR) - e.g., 'ST0050', 'ST1234'",
                "region": "Region (VARCHAR, LOWERCASE) - northeast, southeast, midwest, southwest, west",
                "market": "Market/City (VARCHAR) - e.g., 'Miami, FL', 'Boston, MA'",
                "state": "State (VARCHAR) - e.g., 'Florida', 'Texas'",
                "latitude": "Latitude coordinate (NUMERIC)",
                "longitude": "Longitude coordinate (NUMERIC)"
            },
            
            # Hierarchy
            "location_hierarchy": """
Region → Market → State → Store
Example: southeast → Miami, FL → Florida → ST0050

Regions (LOWERCASE!):
- northeast
- southeast  
- midwest
- southwest
- west
- south
""",
            
            # Join patterns
            "join_patterns": """
-- Location joins with other tables:
-- Sales: sales.store_code = location.location
-- Batches: batches.store_code = location.location
-- Metrics: metrics.location = location.location
-- Events: events.store_id = location.location
-- Weather: weekly_weather.store_id = location.location
""",
            
            # Formulas
            "formulas": [],
            
            # Detected location filters
            "detected_locations": self._detect_locations(query_lower)
        }
        
        # Store count
        if any(word in query_lower for word in ["how many stores", "store count", "number of stores"]):
            hints["formulas"].append({
                "name": "Store Count",
                "sql": "COUNT(DISTINCT l.location) AS store_count",
                "description": "Count of unique stores"
            })
        
        # By region aggregation
        if any(word in query_lower for word in ["by region", "regional", "each region"]):
            hints["formulas"].append({
                "name": "Group by Region",
                "sql": "l.region",
                "description": "Aggregate by region",
                "requires_groupby": "GROUP BY l.region"
            })
        
        # By market aggregation
        if any(word in query_lower for word in ["by market", "each market"]):
            hints["formulas"].append({
                "name": "Group by Market",
                "sql": "l.market",
                "description": "Aggregate by market",
                "requires_groupby": "GROUP BY l.market"
            })
        
        # By state aggregation
        if any(word in query_lower for word in ["by state", "each state"]):
            hints["formulas"].append({
                "name": "Group by State",
                "sql": "l.state",
                "description": "Aggregate by state",
                "requires_groupby": "GROUP BY l.state"
            })
        
        # By store aggregation
        if any(word in query_lower for word in ["by store", "each store", "store level"]):
            hints["formulas"].append({
                "name": "Group by Store",
                "sql": "l.location",
                "description": "Aggregate by individual store",
                "requires_groupby": "GROUP BY l.location"
            })
        
        logger.info(f"📍 LocationAgent provided hints with {len(hints['detected_locations'])} detected locations")
        return hints
    
    def _detect_locations(self, query: str) -> Dict[str, Any]:
        """Detect specific locations mentioned in query"""
        detected = {
            "regions": [],
            "markets": [],
            "states": [],
            "filters": []
        }
        
        # Check regions
        for region in self.REGIONS:
            if region in query:
                detected["regions"].append(region)
                detected["filters"].append(f"l.region = '{region}'")
        
        # Check common markets
        market_keywords = {
            "miami": "Miami, FL",
            "boston": "Boston, MA",
            "chicago": "Chicago, IL",
            "dallas": "Dallas, TX",
            "los angeles": "Los Angeles, CA",
            "columbia": "Columbia, SC"
        }
        
        for keyword, market in market_keywords.items():
            if keyword in query:
                detected["markets"].append(market)
                detected["filters"].append(f"l.market = '{market}'")
        
        # Check states
        state_keywords = {
            "florida": "Florida",
            "texas": "Texas",
            "california": "California",
            "new york": "New York",
            "massachusetts": "Massachusetts"
        }
        
        for keyword, state in state_keywords.items():
            if keyword in query:
                detected["states"].append(state)
                detected["filters"].append(f"l.state = '{state}'")
        
        return detected
    
    def get_example_queries(self) -> List[str]:
        """Return example queries this agent can help with"""
        return [
            "Show sales by region",
            "How many stores in Florida?",
            "What's the performance of Miami market?",
            "Compare Northeast vs Southeast",
            "List all stores in the South region"
        ]


# Global instance
location_agent = LocationAgent()
