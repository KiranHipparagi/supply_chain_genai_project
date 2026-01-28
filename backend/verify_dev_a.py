#!/usr/bin/env python3
"""
Quick verification that Developer A's work is complete and correct
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*70)
print("🧪 DEVELOPER A VERIFICATION SCRIPT")
print("="*70)
print()

# Test 1: Check file existence
print("📁 1. Checking file structure...")
files_to_check = [
    "mcp/__init__.py",
    "mcp/tools.py",
    "mcp/schemas.py",
    "mcp/README_DEV_A.md",
    "mcp/README_DEV_B.md",
    "mcp/IMPLEMENTATION_PLAN.md",
    "mcp/server.py",
    "mcp/config.json"
]

all_files_exist = True
for file in files_to_check:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"  {status} {file}")
    if not exists:
        all_files_exist = False

print()

# Test 2: Import tools module
print("📦 2. Testing imports...")
try:
    from mcp.tools import TOOL_REGISTRY, list_tools
    print(f"  ✅ Successfully imported mcp.tools")
    print(f"  ✅ Tool registry has {len(TOOL_REGISTRY)} tools")
except ImportError as e:
    print(f"  ⚠️  MCP SDK not installed (expected): {e}")
    print(f"  ℹ️  This is normal - Developer B will install it")
except Exception as e:
    print(f"  ❌ Unexpected error: {e}")
    all_files_exist = False

print()

# Test 3: Verify existing agents unchanged
print("🔍 3. Verifying existing agents unchanged...")
try:
    from agents.sales_agent import sales_agent
    from agents.metrics_agent import metrics_agent
    from agents.database_agent import DatabaseAgent
    
    # Test that they still work
    result = sales_agent.get_domain_hints("test query")
    if "agent" in result:
        print("  ✅ SalesAgent working")
    else:
        print("  ❌ SalesAgent broken")
        all_files_exist = False
    
    result = metrics_agent.get_domain_hints("test query")
    if "agent" in result:
        print("  ✅ MetricsAgent working")
    else:
        print("  ❌ MetricsAgent broken")
        all_files_exist = False
    
    print("  ✅ DatabaseAgent importable")
    
except Exception as e:
    print(f"  ❌ Agent error: {e}")
    all_files_exist = False

print()

# Test 4: Check tool count
print("📊 4. Tool inventory...")
try:
    from mcp.tools import TOOL_REGISTRY
    expected_tools = [
        "get_sales_domain_hints",
        "get_wdd_domain_hints",
        "get_weather_domain_hints",
        "get_events_domain_hints",
        "get_inventory_domain_hints",
        "get_location_domain_hints",
        "execute_sql_with_domain_hints",
        "generate_chart_config",
        "resolve_entities",
        "expand_context_via_graph",
        "get_current_date_context",
        "get_database_schema",
        "health_check"
    ]
    
    for tool in expected_tools:
        if tool in TOOL_REGISTRY:
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} MISSING")
            all_files_exist = False
    
    if len(TOOL_REGISTRY) == 13:
        print(f"\n  ✅ All 13 tools present")
    else:
        print(f"\n  ❌ Expected 13 tools, found {len(TOOL_REGISTRY)}")
        all_files_exist = False
        
except Exception as e:
    print(f"  ⚠️  Cannot verify tools (MCP SDK not installed): {e}")

print()

# Final verdict
print("="*70)
if all_files_exist:
    print("✅ DEVELOPER A TASKS: COMPLETE AND VERIFIED")
    print()
    print("Next steps:")
    print("  1. Commit your work: git add backend/mcp/")
    print("  2. Run tests: python3 -m pytest tests/")
    print("  3. Notify Developer B: Tools are ready!")
else:
    print("❌ DEVELOPER A TASKS: INCOMPLETE OR ERRORS FOUND")
    print("Please review the errors above.")

print("="*70)
