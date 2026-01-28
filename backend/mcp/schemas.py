"""
JSON Schemas for MCP Tool Parameters
=====================================

Developer A: Complete ✅

These schemas define the input/output structure for each MCP tool.
Used for type validation and documentation.
"""

from typing import Dict, Any

# ============================================================
# DOMAIN EXPERT TOOL SCHEMAS
# ============================================================

SALES_HINTS_SCHEMA = {
    "name": "get_sales_domain_hints",
    "description": "Get sales-specific domain hints for SQL generation",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "User's natural language query"
            },
            "context": {
                "type": "object",
                "description": "Optional resolved context with products, locations, dates",
                "properties": {
                    "products": {"type": "array"},
                    "locations": {"type": "array"},
                    "dates": {"type": "array"}
                }
            }
        },
        "required": ["query"]
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "agent": {"type": "string"},
            "formulas": {"type": "array"},
            "table_schema": {"type": "object"},
            "key_columns": {"type": "array"},
            "join_hints": {"type": "array"}
        }
    }
}

WDD_HINTS_SCHEMA = {
    "name": "get_wdd_domain_hints",
    "description": "Get Weather-Driven Demand (WDD) analysis hints",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "User's natural language query"
            },
            "context": {
                "type": "object",
                "description": "Optional resolved context"
            }
        },
        "required": ["query"]
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "agent": {"type": "string"},
            "formulas": {"type": "array"},
            "temporal_logic": {"type": "object"},
            "table_schema": {"type": "object"}
        }
    }
}

WEATHER_HINTS_SCHEMA = {
    "name": "get_weather_domain_hints",
    "description": "Get weather condition analysis hints",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "context": {"type": "object"}
        },
        "required": ["query"]
    }
}

EVENTS_HINTS_SCHEMA = {
    "name": "get_events_domain_hints",
    "description": "Get event analysis hints",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "context": {"type": "object"}
        },
        "required": ["query"]
    }
}

INVENTORY_HINTS_SCHEMA = {
    "name": "get_inventory_domain_hints",
    "description": "Get inventory analysis hints",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "context": {"type": "object"}
        },
        "required": ["query"]
    }
}

LOCATION_HINTS_SCHEMA = {
    "name": "get_location_domain_hints",
    "description": "Get geographic/location analysis hints",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "context": {"type": "object"}
        },
        "required": ["query"]
    }
}


# ============================================================
# EXECUTION TOOL SCHEMAS
# ============================================================

EXECUTE_SQL_SCHEMA = {
    "name": "execute_sql_with_domain_hints",
    "description": "Generate and execute SQL query using domain expert hints",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "User's natural language query"
            },
            "context": {
                "type": "object",
                "description": "Resolved context (products, locations, dates, events)"
            },
            "domain_hints": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of hints from domain expert tools"
            }
        },
        "required": ["query"]
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "sql_query": {"type": "string"},
            "data": {"type": "array"},
            "row_count": {"type": "integer"},
            "analysis": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "no_data", "error"]}
        }
    }
}

GENERATE_CHART_SCHEMA = {
    "name": "generate_chart_config",
    "description": "Generate Google Charts configuration from query results",
    "inputSchema": {
        "type": "object",
        "properties": {
            "db_result": {
                "type": "object",
                "description": "Database query result with 'data' field"
            },
            "chart_type": {
                "type": "string",
                "description": "Chart type: auto, ColumnChart, BarChart, LineChart, etc.",
                "default": "auto"
            },
            "query": {
                "type": "string",
                "description": "Original user query for context"
            }
        },
        "required": ["db_result"]
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "chartType": {"type": "string"},
            "data": {"type": "array"},
            "options": {"type": "object"}
        }
    }
}


# ============================================================
# RESOLUTION TOOL SCHEMAS
# ============================================================

RESOLVE_ENTITIES_SCHEMA = {
    "name": "resolve_entities",
    "description": "Resolve entities from natural language using Azure AI Search",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "User's natural language query"
            }
        },
        "required": ["query"]
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "products": {"type": "array"},
            "locations": {"type": "array"},
            "events": {"type": "array"},
            "dates": {"type": "array"}
        }
    }
}

EXPAND_CONTEXT_SCHEMA = {
    "name": "expand_context_via_graph",
    "description": "Expand entity context using Cosmos DB Gremlin knowledge graph",
    "inputSchema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "object",
                "description": "Resolved entities from resolve_entities tool",
                "properties": {
                    "products": {"type": "array"},
                    "locations": {"type": "array"}
                }
            }
        },
        "required": ["entities"]
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "expanded_products": {"type": "array"},
            "expanded_locations": {"type": "array"},
            "related_events": {"type": "array"}
        }
    }
}


# ============================================================
# UTILITY TOOL SCHEMAS
# ============================================================

DATE_CONTEXT_SCHEMA = {
    "name": "get_current_date_context",
    "description": "Get current date context for the demo data",
    "inputSchema": {
        "type": "object",
        "properties": {}
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "current_weekend": {"type": "string"},
            "current_date_formatted": {"type": "string"},
            "this_week": {"type": "string"},
            "next_week": {"type": "string"},
            "last_week": {"type": "string"},
            "next_month": {"type": "object"},
            "last_month": {"type": "object"},
            "last_year": {"type": "integer"}
        }
    }
}

DATABASE_SCHEMA_SCHEMA = {
    "name": "get_database_schema",
    "description": "Get database schema information",
    "inputSchema": {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Optional table name for specific schema",
                "enum": [
                    "calendar", "product_hierarchy", "perishable", "location",
                    "events", "weekly_weather", "metrics", "sales", "batches",
                    "batch_stock_tracking", "spoilage_report"
                ]
            }
        }
    },
    "outputSchema": {
        "type": "object"
    }
}

HEALTH_CHECK_SCHEMA = {
    "name": "health_check",
    "description": "Check health of all Planalytics services",
    "inputSchema": {
        "type": "object",
        "properties": {}
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "postgresql": {"type": "string"},
            "azure_search": {"type": "string"},
            "gremlin": {"type": "string"},
            "timestamp": {"type": "string"}
        }
    }
}


# ============================================================
# SCHEMA REGISTRY
# ============================================================

SCHEMA_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_sales_domain_hints": SALES_HINTS_SCHEMA,
    "get_wdd_domain_hints": WDD_HINTS_SCHEMA,
    "get_weather_domain_hints": WEATHER_HINTS_SCHEMA,
    "get_events_domain_hints": EVENTS_HINTS_SCHEMA,
    "get_inventory_domain_hints": INVENTORY_HINTS_SCHEMA,
    "get_location_domain_hints": LOCATION_HINTS_SCHEMA,
    "execute_sql_with_domain_hints": EXECUTE_SQL_SCHEMA,
    "generate_chart_config": GENERATE_CHART_SCHEMA,
    "resolve_entities": RESOLVE_ENTITIES_SCHEMA,
    "expand_context_via_graph": EXPAND_CONTEXT_SCHEMA,
    "get_current_date_context": DATE_CONTEXT_SCHEMA,
    "get_database_schema": DATABASE_SCHEMA_SCHEMA,
    "health_check": HEALTH_CHECK_SCHEMA,
}


def get_schema(tool_name: str) -> Dict[str, Any]:
    """Get schema for a specific tool"""
    return SCHEMA_REGISTRY.get(tool_name, {})


def list_schemas() -> list:
    """List all available schemas"""
    return list(SCHEMA_REGISTRY.keys())


if __name__ == "__main__":
    import json
    print("📋 MCP Tool Schemas")
    print(f"Total schemas: {len(SCHEMA_REGISTRY)}\n")
    
    for tool_name, schema in SCHEMA_REGISTRY.items():
        print(f"\n{'='*60}")
        print(f"Tool: {tool_name}")
        print(f"{'='*60}")
        print(json.dumps(schema, indent=2))
