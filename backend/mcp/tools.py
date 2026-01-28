"""
MCP Tool Definitions for Planalytics AI
========================================

All 13 tools are wrappers around existing agent methods.
NO modification to original agent files required.

Developer A: Complete ✅
Developer B: Use these tools in server.py

Tools:
1-6: Domain Expert Tools (hints)
7-8: Execution Tools (SQL, charts)
9-10: Resolution Tools (entities, graph)
11-13: Utility Tools (schema, dates, health)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# MCP imports (graceful degradation if not installed)
MCP_AVAILABLE = False
try:
    from mcp.server import Server
    MCP_AVAILABLE = True
except ImportError:
    # Stub for development before MCP SDK installation
    class Server:
        def __init__(self, name): 
            self.name = name
            self._tools = {}
        
        def tool(self, description: str = None):
            def decorator(func):
                self._tools[func.__name__] = func
                return func
            return decorator

# Import existing agents (NO MODIFICATIONS to these files!)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.sales_agent import sales_agent
from agents.metrics_agent import metrics_agent
from agents.weather_agent import weather_agent
from agents.events_agent import events_agent
from agents.inventory_agent import inventory_agent
from agents.location_agent import location_agent
from agents.database_agent import DatabaseAgent
from agents.visualization_agent import VisualizationAgent
from services.context_resolver import context_resolver, CURRENT_WEEK_END
from database.azure_search import azure_search
from database.gremlin_db import gremlin_conn
from database.postgres_db import get_db
from core.logger import logger
from sqlalchemy import text

# Initialize MCP server
mcp_server = Server("planalytics-supply-chain")


# ============================================================
# DOMAIN EXPERT TOOLS (6 tools)
# ============================================================

@mcp_server.tool(description="Get sales-specific domain hints for SQL generation")
async def get_sales_domain_hints(query: str, context: dict = None) -> dict:
    """
    Get sales-specific domain hints for SQL generation.
    
    Provides:
    - Sales table schema (sales_units, total_amount, transaction_date)
    - Revenue formula: SUM(sales_units * total_amount)
    - Week-on-week change formulas
    - Daily sales velocity calculations
    
    Args:
        query: User's natural language query
        context: Optional resolved context (products, locations, dates)
    
    Returns:
        Sales domain hints with schemas, formulas, join patterns
    
    Example:
        hints = await get_sales_domain_hints("revenue by region last week")
        # Returns: {"agent": "SalesAgent", "formulas": [...], "table_schema": {...}}
    """
    try:
        result = sales_agent.get_domain_hints(query, context)
        logger.info(f"✅ Sales hints retrieved for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in get_sales_domain_hints: {e}")
        return {"error": str(e), "agent": "SalesAgent"}


@mcp_server.tool(description="Get Weather-Driven Demand (WDD) analysis hints")
async def get_wdd_domain_hints(query: str, context: dict = None) -> dict:
    """
    Get Weather-Driven Demand (WDD) analysis hints.
    
    CRITICAL: metrics table contains TREND VALUES, not actual sales!
    - Use metric vs metric_nrm for FUTURE queries (≤4 weeks)
    - Use metric vs metric_ly for PAST/YoY queries (>4 weeks)
    
    Provides:
    - WDD calculation formulas
    - Recommended order quantity formula
    - Adjusted demand/velocity formulas
    - Temporal logic for metric selection
    
    Args:
        query: User's natural language query
        context: Optional resolved context
    
    Returns:
        WDD domain hints with temporal logic
    
    Example:
        hints = await get_wdd_domain_hints("weather impact on Ice Cream next week")
    """
    try:
        result = metrics_agent.get_domain_hints(query, context)
        logger.info(f"✅ WDD hints retrieved for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in get_wdd_domain_hints: {e}")
        return {"error": str(e), "agent": "MetricsAgent"}


@mcp_server.tool(description="Get weather condition analysis hints")
async def get_weather_domain_hints(query: str, context: dict = None) -> dict:
    """
    Get weather condition analysis hints.
    
    Provides:
    - Weather flags (heatwave_flag, cold_spell_flag, heavy_rain_flag, snow_flag)
    - Temperature columns (tmax_f, tmin_f, avg_temp_f)
    - Ideal beach weather definition
    - Weather-demand correlation patterns
    
    Args:
        query: User's natural language query
        context: Optional resolved context
    
    Returns:
        Weather domain hints with flags and conditions
    
    Example:
        hints = await get_weather_domain_hints("heatwave impact on beverage sales")
    """
    try:
        result = weather_agent.get_domain_hints(query, context)
        logger.info(f"✅ Weather hints retrieved for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in get_weather_domain_hints: {e}")
        return {"error": str(e), "agent": "WeatherAgent"}


@mcp_server.tool(description="Get event analysis hints for holidays, sports, festivals")
async def get_events_domain_hints(query: str, context: dict = None) -> dict:
    """
    Get event analysis hints for holidays, sports, festivals.
    
    Provides:
    - Events table schema
    - Event types (Sports, Concert, Festival, Holiday)
    - Event proximity checking (7-day window pattern)
    - No-event filtering patterns
    
    Args:
        query: User's natural language query
        context: Optional resolved context
    
    Returns:
        Events domain hints with proximity logic
    
    Example:
        hints = await get_events_domain_hints("sales during holiday events")
    """
    try:
        result = events_agent.get_domain_hints(query, context)
        logger.info(f"✅ Events hints retrieved for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in get_events_domain_hints: {e}")
        return {"error": str(e), "agent": "EventsAgent"}


@mcp_server.tool(description="Get inventory analysis hints for batches, stock, spoilage")
async def get_inventory_domain_hints(query: str, context: dict = None) -> dict:
    """
    Get inventory analysis hints for batches, stock, spoilage.
    
    CRITICAL: perishable.max_period is TEXT - MUST CAST TO INTEGER!
    
    Provides:
    - Batches table schema (stock_at_week_end, expiry_date)
    - Weeks of Cover (WOC) formula: current_stock / avg_weekly_sales
    - Stockout risk calculation (HIGH < 1 week, MEDIUM 1-2 weeks)
    - Spoilage/shrinkage formulas
    - Shelf-life risk calculations
    
    Args:
        query: User's natural language query
        context: Optional resolved context
    
    Returns:
        Inventory domain hints with CFO formulas
    
    Example:
        hints = await get_inventory_domain_hints("products at risk of stockout")
    """
    try:
        result = inventory_agent.get_domain_hints(query, context)
        logger.info(f"✅ Inventory hints retrieved for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in get_inventory_domain_hints: {e}")
        return {"error": str(e), "agent": "InventoryAgent"}


@mcp_server.tool(description="Get geographic/location analysis hints")
async def get_location_domain_hints(query: str, context: dict = None) -> dict:
    """
    Get geographic/location analysis hints.
    
    CRITICAL: Region values are LOWERCASE ('northeast', not 'Northeast')
    
    Provides:
    - Location hierarchy (Region → Market → State → Store)
    - Available regions: northeast, southeast, midwest, southwest, west, south
    - Geographic aggregation patterns
    - Store count formulas
    
    Args:
        query: User's natural language query
        context: Optional resolved context
    
    Returns:
        Location domain hints with hierarchy info
    
    Example:
        hints = await get_location_domain_hints("sales by region")
    """
    try:
        result = location_agent.get_domain_hints(query, context)
        logger.info(f"✅ Location hints retrieved for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in get_location_domain_hints: {e}")
        return {"error": str(e), "agent": "LocationAgent"}


# ============================================================
# EXECUTION TOOLS (2 tools)
# ============================================================

@mcp_server.tool(description="Generate and execute SQL query using domain expert hints")
async def execute_sql_with_domain_hints(
    query: str,
    context: dict = None,
    domain_hints: list = None
) -> dict:
    """
    Generate and execute SQL query using domain expert hints.
    
    THIS IS THE ONLY TOOL THAT EXECUTES SQL.
    
    Workflow:
    1. Resolve entities if context not provided
    2. Combine domain hints from relevant experts
    3. Generate optimized PostgreSQL SQL with LLM (o3-mini)
    4. Execute query on PostgreSQL database
    5. Return structured results with analysis
    
    Args:
        query: User's natural language query
        context: Resolved context (products, locations, dates, events)
        domain_hints: List of hints from domain expert tools
    
    Returns:
        {
            "sql_query": "SELECT ...",
            "data": [...],
            "row_count": 25,
            "analysis": "Natural language summary of results",
            "status": "success" | "no_data" | "error"
        }
    
    Example workflow:
        # Step 1: Get relevant domain hints
        sales_hints = await get_sales_domain_hints("revenue by region")
        location_hints = await get_location_domain_hints("by region")
        
        # Step 2: Execute query with hints
        result = await execute_sql_with_domain_hints(
            query="Show total revenue by region last week",
            domain_hints=[sales_hints, location_hints]
        )
    """
    try:
        db_agent = DatabaseAgent()
        result = db_agent.query_with_hints(query, context, domain_hints or [])
        logger.info(f"✅ SQL executed for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in execute_sql_with_domain_hints: {e}")
        return {
            "status": "error",
            "error": str(e),
            "sql_query": None,
            "data": []
        }


@mcp_server.tool(description="Generate Google Charts configuration from query results")
async def generate_chart_config(
    db_result: dict,
    chart_type: str = "auto",
    query: str = ""
) -> dict:
    """
    Generate Google Charts configuration from query results.
    
    LLM-powered smart visualization that:
    - Analyzes data structure automatically
    - Selects optimal chart type if "auto"
    - Creates valid Google Charts JSON configuration
    
    Supported chart types:
    - ColumnChart: Category comparisons (<10 categories)
    - BarChart: Horizontal comparisons (many categories)
    - LineChart: Time series, trends
    - PieChart: Distribution, proportions (<10 slices)
    - AreaChart: Cumulative trends
    - ScatterChart: Correlations between two variables
    - GeoChart: Geographic/map data
    - Table: Detailed data display
    
    Args:
        db_result: Database query result with 'data' field
        chart_type: "auto" | "ColumnChart" | "BarChart" | "LineChart" | etc.
        query: Original user query for context
    
    Returns:
        {
            "chartType": "ColumnChart",
            "data": [["Header", "Value"], ["Category A", 100], ["Category B", 200]],
            "options": {
                "title": "Chart Title",
                "colors": ["#D04A02", "#3B82F6"],
                "legend": {"position": "top"},
                ...
            }
        }
    
    Example:
        result = await execute_sql_with_domain_hints("sales by region")
        chart = await generate_chart_config(result, chart_type="ColumnChart")
    """
    try:
        viz_agent = VisualizationAgent()
        result = viz_agent.generate_chart_config(db_result, chart_type, query)
        logger.info(f"✅ Chart config generated: {chart_type}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in generate_chart_config: {e}")
        return {
            "chartType": "Table",
            "data": [],
            "error": str(e)
        }


# ============================================================
# RESOLUTION TOOLS (2 tools)
# ============================================================

@mcp_server.tool(description="Resolve entities from natural language using Azure AI Search")
async def resolve_entities(query: str) -> dict:
    """
    Resolve entities from natural language query using Azure AI Search.
    
    Uses vector search (text-embedding-ada-002) + semantic matching across:
    - planalytics-index-products (product names, categories, departments)
    - planalytics-index-locations (stores, markets, regions, states)
    - planalytics-index-events (event names, types, dates)
    - planalytics-index-calendar (dates, weeks, months, seasons)
    
    Example:
        result = await resolve_entities("Ice Cream sales in Miami last week")
        # Returns:
        {
            "products": [{"product": "Ice Cream", "category": "Dairy", "dept": "Grocery"}],
            "locations": [{"market": "Miami, FL", "region": "southeast", "state": "Florida"}],
            "events": [],
            "dates": [{"end_date": "2025-11-01", "month": "November", "week": 44}]
        }
    
    Args:
        query: User's natural language query
    
    Returns:
        {
            "products": [...],
            "locations": [...],
            "events": [...],
            "dates": [...]
        }
    """
    try:
        result = azure_search.resolve_entities(query)
        logger.info(f"✅ Entities resolved for: {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in resolve_entities: {e}")
        return {
            "products": [],
            "locations": [],
            "events": [],
            "dates": [],
            "error": str(e)
        }


@mcp_server.tool(description="Expand entity context using Cosmos DB Gremlin knowledge graph")
async def expand_context_via_graph(entities: dict) -> dict:
    """
    Expand entity context using Cosmos DB Gremlin knowledge graph.
    
    Takes resolved entities and expands via graph relationships:
    - Products → Related products in same category/department
    - Locations → Other stores in same market/region
    - Events → Related event types
    
    Args:
        entities: Resolved entities from resolve_entities tool
            {
                "products": [{"id": "P_1", "product": "Ice Cream"}],
                "locations": [{"id": "LOC_50", "market": "Miami, FL"}]
            }
    
    Returns:
        {
            "expanded_products": [{"product_id": "P_2", "product": "Frozen Yogurt", "category": "Dairy"}],
            "expanded_locations": [{"store_id": "ST0051", "market": "Miami, FL"}],
            "related_events": [{"event_name": "Summer Festival", "event_type": "Festival"}]
        }
    
    Example:
        entities = await resolve_entities("Ice Cream in Miami")
        expanded = await expand_context_via_graph(entities)
    """
    try:
        result = context_resolver._expand_context_via_graph(entities)
        logger.info(f"✅ Context expanded via graph")
        return result
    except Exception as e:
        logger.error(f"❌ Error in expand_context_via_graph: {e}")
        return {
            "expanded_products": [],
            "expanded_locations": [],
            "related_events": [],
            "error": str(e)
        }


# ============================================================
# UTILITY TOOLS (3 tools)
# ============================================================

@mcp_server.tool(description="Get current date context for the demo data")
async def get_current_date_context() -> dict:
    """
    Get current date context for the demo data.
    
    CRITICAL for all date-relative queries! The demo data is centered around
    November 8, 2025 as the "current" date.
    
    Returns:
        {
            "current_weekend": "2025-11-08",
            "current_date_formatted": "November 8, 2025",
            "this_week": "2025-11-08",
            "next_week": "2025-11-15",
            "last_week": "2025-11-01",
            "next_month": {"month": "December", "year": 2025},
            "last_month": {"month": "October", "year": 2025},
            "last_year": 2024,
            "critical_note": "calendar.month is STRING type ('January'), not integer!"
        }
    
    Example:
        date_ctx = await get_current_date_context()
        # Use date_ctx["next_week"] for queries about "next week"
    """
    try:
        from datetime import datetime, timedelta
        
        current_date = datetime(2025, 11, 8)
        next_week = current_date + timedelta(weeks=1)
        last_week = current_date - timedelta(weeks=1)
        
        return {
            "current_weekend": CURRENT_WEEK_END,
            "current_date_formatted": current_date.strftime("%B %d, %Y"),
            "this_week": CURRENT_WEEK_END,
            "next_week": next_week.strftime("%Y-%m-%d"),
            "last_week": last_week.strftime("%Y-%m-%d"),
            "next_2_weeks": [
                (current_date + timedelta(weeks=1)).strftime("%Y-%m-%d"),
                (current_date + timedelta(weeks=2)).strftime("%Y-%m-%d")
            ],
            "last_4_weeks": [
                (current_date - timedelta(weeks=i)).strftime("%Y-%m-%d") 
                for i in range(3, -1, -1)
            ],
            "next_month": {"month": "December", "year": 2025},
            "last_month": {"month": "October", "year": 2025},
            "last_year": 2024,
            "current_quarter": 4,
            "last_quarter": 3,
            "critical_note": "calendar.month is STRING type ('January', 'February'), NOT integer!",
            "region_note": "location.region is LOWERCASE ('northeast', 'southeast')"
        }
    except Exception as e:
        logger.error(f"❌ Error in get_current_date_context: {e}")
        return {"error": str(e)}


@mcp_server.tool(description="Get database schema information for SQL generation")
async def get_database_schema(table_name: str = None) -> dict:
    """
    Get database schema information for SQL generation.
    
    If table_name is provided, returns detailed schema for that table.
    If not provided, returns overview of all 11 tables.
    
    Args:
        table_name: Optional - one of: calendar, product_hierarchy, perishable,
                    location, events, weekly_weather, metrics, sales, batches,
                    batch_stock_tracking, spoilage_report
    
    Returns:
        Schema information including columns, types, join relationships
    
    Example:
        # Get overview
        all_schemas = await get_database_schema()
        
        # Get specific table
        metrics_schema = await get_database_schema("metrics")
    """
    try:
        schemas = {
            "calendar": {
                "description": "NRF Calendar - date dimension",
                "columns": {
                    "end_date": "DATE - Week ending date (PK for joins)",
                    "year": "INTEGER - 2023, 2024, 2025, 2026",
                    "quarter": "INTEGER - 1, 2, 3, 4",
                    "month": "VARCHAR - STRING! ('January', 'February', etc.)",
                    "week": "INTEGER - Week number 1-52",
                    "season": "VARCHAR - 'Spring', 'Summer', 'Fall', 'Winter'"
                },
                "critical_note": "month is STRING, not integer!"
            },
            "product_hierarchy": {
                "description": "Product dimension with hierarchy",
                "columns": {
                    "product_id": "INTEGER - Primary key",
                    "dept": "VARCHAR - Department (may be NULL for sector products)",
                    "category": "VARCHAR - Category (may be NULL)",
                    "product": "VARCHAR - Product name"
                },
                "critical_note": "Some products have NULL dept/category"
            },
            "perishable": {
                "description": "Perishable product info",
                "columns": {
                    "product": "VARCHAR - Product name (joins with product_hierarchy.product)",
                    "max_period": "TEXT - Shelf life value - MUST CAST TO INTEGER!",
                    "period_metric": "VARCHAR - 'Days' or 'Weeks'",
                    "storage": "VARCHAR - 'Freezer', 'Refrigerator', 'Ambient'"
                },
                "critical_note": "CAST(max_period AS INTEGER) for arithmetic!"
            },
            "location": {
                "description": "Store/location dimension",
                "columns": {
                    "location": "VARCHAR - Store ID (e.g., 'ST0050')",
                    "region": "VARCHAR - LOWERCASE! ('northeast', 'southeast', etc.)",
                    "market": "VARCHAR - City, State (e.g., 'Miami, FL')",
                    "state": "VARCHAR - Full state name",
                    "latitude": "NUMERIC",
                    "longitude": "NUMERIC"
                },
                "critical_note": "region is LOWERCASE!"
            },
            "events": {
                "description": "Events mapped to store proximity",
                "columns": {
                    "event": "VARCHAR - Event name",
                    "event_type": "VARCHAR - 'Sports', 'Concert', 'Festival', 'Holiday'",
                    "event_date": "DATE - Event date",
                    "store_id": "VARCHAR - Store in proximity"
                }
            },
            "weekly_weather": {
                "description": "Weekly weather conditions by store",
                "columns": {
                    "store_id": "VARCHAR - Store ID",
                    "week_end_date": "DATE - Week ending date",
                    "avg_temp_f": "NUMERIC - Average temperature",
                    "tmax_f": "NUMERIC - Max temperature",
                    "tmin_f": "NUMERIC - Min temperature",
                    "precip_in": "NUMERIC - Precipitation inches",
                    "heatwave_flag": "BOOLEAN",
                    "cold_spell_flag": "BOOLEAN",
                    "heavy_rain_flag": "BOOLEAN",
                    "snow_flag": "BOOLEAN"
                }
            },
            "metrics": {
                "description": "WDD TREND data - NOT actual sales!",
                "columns": {
                    "product": "VARCHAR - Product NAME (not ID!)",
                    "location": "VARCHAR - Store ID",
                    "end_date": "DATE - Week ending date",
                    "metric": "NUMERIC - WDD trend value",
                    "metric_nrm": "NUMERIC - Normal demand (use for FUTURE ≤4 weeks)",
                    "metric_ly": "NUMERIC - Last year demand (use for PAST/YoY)"
                },
                "critical_note": "These are TREND VALUES, not actual sales! Join on product NAME."
            },
            "sales": {
                "description": "Actual sales transactions",
                "columns": {
                    "product_code": "INTEGER - FK to product_hierarchy.product_id",
                    "store_code": "VARCHAR - FK to location.location",
                    "transaction_date": "DATE - Sale date",
                    "sales_units": "INTEGER - Units sold",
                    "total_amount": "NUMERIC - Revenue per unit"
                },
                "formula": "Revenue = SUM(sales_units * total_amount)"
            },
            "batches": {
                "description": "Inventory batches with expiry",
                "columns": {
                    "batch_id": "VARCHAR - Batch identifier",
                    "product_code": "INTEGER - FK to product_hierarchy.product_id",
                    "store_code": "VARCHAR - FK to location.location",
                    "expiry_date": "DATE - Expiration date",
                    "stock_at_week_end": "INTEGER - Current stock level",
                    "week_end_date": "DATE - Snapshot date"
                }
            },
            "batch_stock_tracking": {
                "description": "Stock movement transactions",
                "columns": {
                    "batch_id": "VARCHAR - Batch identifier",
                    "transaction_type": "VARCHAR - 'sale', 'transfer', 'adjustment', 'spoilage'",
                    "transaction_date": "DATE",
                    "qty_change": "INTEGER - Quantity change"
                }
            },
            "spoilage_report": {
                "description": "Spoilage/waste tracking",
                "columns": {
                    "product_code": "INTEGER",
                    "store_code": "VARCHAR",
                    "spoilage_qty": "INTEGER - Units spoiled",
                    "spoilage_pct": "NUMERIC - Spoilage percentage"
                }
            }
        }
        
        if table_name:
            if table_name in schemas:
                return {"table": table_name, "schema": schemas[table_name]}
            else:
                return {
                    "error": f"Unknown table: {table_name}",
                    "available_tables": list(schemas.keys())
                }
        
        return {"tables": {k: v["description"] for k, v in schemas.items()}}
    except Exception as e:
        logger.error(f"❌ Error in get_database_schema: {e}")
        return {"error": str(e)}


@mcp_server.tool(description="Check health of all Planalytics services")
async def health_check() -> dict:
    """
    Check health of all Planalytics services.
    
    Returns status of:
    - PostgreSQL database connection
    - Azure AI Search service
    - Cosmos DB Gremlin graph
    
    Returns:
        {
            "postgresql": "healthy" | "error: <message>",
            "azure_search": "healthy" | "error: <message>",
            "gremlin": "healthy" | "disconnected",
            "timestamp": "2025-11-08T10:30:00"
        }
    
    Example:
        status = await health_check()
        if status["postgresql"] != "healthy":
            print("Database issue!")
    """
    status = {
        "postgresql": "unknown",
        "azure_search": "unknown",
        "gremlin": "unknown",
        "timestamp": datetime.now().isoformat()
    }
    
    # Check PostgreSQL
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
        status["postgresql"] = "healthy"
    except Exception as e:
        status["postgresql"] = f"error: {str(e)[:100]}"
        logger.error(f"PostgreSQL health check failed: {e}")
    
    # Check Azure Search
    try:
        results = azure_search.search_products("test", top_k=1)
        status["azure_search"] = "healthy"
    except Exception as e:
        status["azure_search"] = f"error: {str(e)[:100]}"
        logger.error(f"Azure Search health check failed: {e}")
    
    # Check Gremlin
    try:
        if gremlin_conn.ensure_connected():
            status["gremlin"] = "healthy"
        else:
            status["gremlin"] = "disconnected"
    except Exception as e:
        status["gremlin"] = f"error: {str(e)[:100]}"
        logger.error(f"Gremlin health check failed: {e}")
    
    return status


# ============================================================
# TOOL REGISTRY (for programmatic access)
# ============================================================

TOOL_REGISTRY = {
    # Domain Expert Tools
    "get_sales_domain_hints": get_sales_domain_hints,
    "get_wdd_domain_hints": get_wdd_domain_hints,
    "get_weather_domain_hints": get_weather_domain_hints,
    "get_events_domain_hints": get_events_domain_hints,
    "get_inventory_domain_hints": get_inventory_domain_hints,
    "get_location_domain_hints": get_location_domain_hints,
    
    # Execution Tools
    "execute_sql_with_domain_hints": execute_sql_with_domain_hints,
    "generate_chart_config": generate_chart_config,
    
    # Resolution Tools
    "resolve_entities": resolve_entities,
    "expand_context_via_graph": expand_context_via_graph,
    
    # Utility Tools
    "get_current_date_context": get_current_date_context,
    "get_database_schema": get_database_schema,
    "health_check": health_check,
}


def list_tools() -> list:
    """List all available MCP tools"""
    return list(TOOL_REGISTRY.keys())


def get_tool(name: str):
    """Get a tool by name"""
    return TOOL_REGISTRY.get(name)


# ============================================================
# TESTING UTILITIES
# ============================================================

async def test_all_tools():
    """Test all tools to ensure they work correctly"""
    print("🧪 Testing all MCP tools...\n")
    
    test_results = {}
    
    # Test domain expert tools
    print("1️⃣ Testing Domain Expert Tools...")
    try:
        result = await get_sales_domain_hints("revenue by region")
        test_results["get_sales_domain_hints"] = "✅ PASS" if "agent" in result else "❌ FAIL"
    except Exception as e:
        test_results["get_sales_domain_hints"] = f"❌ ERROR: {e}"
    
    try:
        result = await get_wdd_domain_hints("weather impact")
        test_results["get_wdd_domain_hints"] = "✅ PASS" if "agent" in result else "❌ FAIL"
    except Exception as e:
        test_results["get_wdd_domain_hints"] = f"❌ ERROR: {e}"
    
    # Test utility tools
    print("\n2️⃣ Testing Utility Tools...")
    try:
        result = await get_current_date_context()
        test_results["get_current_date_context"] = "✅ PASS" if "current_weekend" in result else "❌ FAIL"
    except Exception as e:
        test_results["get_current_date_context"] = f"❌ ERROR: {e}"
    
    try:
        result = await get_database_schema()
        test_results["get_database_schema"] = "✅ PASS" if "tables" in result else "❌ FAIL"
    except Exception as e:
        test_results["get_database_schema"] = f"❌ ERROR: {e}"
    
    try:
        result = await health_check()
        test_results["health_check"] = "✅ PASS" if "postgresql" in result else "❌ FAIL"
    except Exception as e:
        test_results["health_check"] = f"❌ ERROR: {e}"
    
    # Print results
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    for tool_name, result in test_results.items():
        print(f"{tool_name}: {result}")
    print("="*60)
    
    return test_results


if __name__ == "__main__":
    import asyncio
    print("🚀 Planalytics MCP Tools")
    print(f"📦 Total tools: {len(TOOL_REGISTRY)}")
    print(f"📋 Available tools: {', '.join(list_tools())}\n")
    
    # Run tests
    asyncio.run(test_all_tools())
