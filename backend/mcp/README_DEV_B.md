# 🏗️ Developer B: MCP Server Implementation

**Status**: 🟡 **TODO - Needs Implementation**

---

## 📋 Your Responsibilities

You are responsible for **building the MCP server infrastructure** that exposes Developer A's tools via the Model Context Protocol.

### What You Need to Do

| File | Status | Your Task |
|------|--------|-----------|
| `server.py` | 🟡 Skeleton | Implement MCP server with stdio transport |
| `config.json` | ✅ Template | Update with correct credentials |
| `requirements.txt` | 🟡 TODO | Add `mcp` dependency |
| `README_DEV_B.md` | ✅ This file | Follow this guide |

---

## 🎯 Your Tasks (3-4 days)

### Day 1: MCP SDK Setup & Basic Server (6 hours)

#### Step 1.1: Install MCP SDK (30 mins)

```bash
cd /home/kiran/Documents/planalytics-genai-solution/backend

# Install MCP Python SDK
pip install mcp

# Update requirements.txt
echo "mcp==0.9.0  # Model Context Protocol SDK" >> requirements.txt
```

#### Step 1.2: Verify Developer A's Tools Work (1 hour)

```bash
# Test the tools
python -m mcp.tools
```

**Expected Output:**
```
🚀 Planalytics MCP Tools
📦 Total tools: 13
📋 Available tools: get_sales_domain_hints, ...

🧪 Testing all MCP tools...
✅ All tests passing
```

**If tests fail:** Contact Developer A before proceeding.

#### Step 1.3: Implement Basic MCP Server (4 hours)

Edit `backend/mcp/server.py`:

```python
"""
MCP Server for Planalytics Tools
"""
import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Import tools from Developer A
from .tools import mcp_server, TOOL_REGISTRY, list_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("planalytics-mcp")


async def main():
    """Start MCP server"""
    logger.info("🚀 Starting Planalytics MCP Server...")
    logger.info(f"📦 Loaded {len(TOOL_REGISTRY)} tools")
    
    # Start server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        init_options = mcp_server.create_initialization_options()
        
        await mcp_server.run(
            read_stream,
            write_stream,
            init_options
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped")
```

#### Step 1.4: Test Local Server (30 mins)

```bash
# Start server
python -m mcp.server

# Should see:
# 🚀 Starting Planalytics MCP Server...
# 📦 Loaded 13 tools
# ✅ Server running on stdio
```

---

### Day 2: Claude Desktop Integration (8 hours)

#### Step 2.1: Update Configuration File (1 hour)

Edit `backend/mcp/config.json`:

```json
{
  "mcpServers": {
    "planalytics": {
      "command": "python",
      "args": ["-m", "backend.mcp.server"],
      "cwd": "/home/kiran/Documents/planalytics-genai-solution",
      "env": {
        "PYTHONPATH": "/home/kiran/Documents/planalytics-genai-solution",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "YOUR_ACTUAL_PASSWORD",
        "POSTGRES_DB": "planalytics_database",
        "OPENAI_ENDPOINT": "YOUR_AZURE_OPENAI_ENDPOINT",
        "OPENAI_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

**IMPORTANT:** Update passwords and API keys!

#### Step 2.2: Install Claude Desktop Config (1 hour)

```bash
# Linux
mkdir -p ~/.config/Claude
cp backend/mcp/config.json ~/.config/Claude/claude_desktop_config.json

# Mac
mkdir -p ~/Library/Application\ Support/Claude
cp backend/mcp/config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows
# Copy to: %APPDATA%\Claude\claude_desktop_config.json
```

#### Step 2.3: Test with Claude Desktop (2 hours)

1. **Restart Claude Desktop** (important!)

2. **Verify Tools Loaded:**
   - Open Claude Desktop
   - Type: "What tools do you have?"
   - Should list all 13 Planalytics tools

3. **Test Simple Query:**
   ```
   User: "Check the health of Planalytics services"
   Claude: [Calls health_check tool automatically]
   ```

4. **Test Complex Workflow:**
   ```
   User: "What products need replenishment in Miami?"
   Claude: 
   1. Calls resolve_entities("products need replenishment in Miami")
   2. Calls get_inventory_domain_hints(...)
   3. Calls execute_sql_with_domain_hints(...)
   4. Returns answer with data
   ```

#### Step 2.4: Debugging (4 hours)

Common issues and fixes:

**Issue 1: Tools not appearing in Claude**
```bash
# Check server logs
python -m mcp.server 2>&1 | tee server.log

# Verify config path
cat ~/.config/Claude/claude_desktop_config.json  # Linux
```

**Issue 2: Tool calls fail**
```python
# Test tools directly
python -c "
import asyncio
from mcp.tools import health_check
print(asyncio.run(health_check()))
"
```

**Issue 3: Import errors**
```bash
# Verify PYTHONPATH
echo $PYTHONPATH

# Should include: /home/kiran/Documents/planalytics-genai-solution
```

---

### Day 3: FastAPI Integration (8 hours)

#### Step 3.1: Create HTTP Endpoint for MCP Tools (4 hours)

Create `backend/routes/mcp_endpoint.py`:

```python
"""
FastAPI endpoint to expose MCP tools via HTTP
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import asyncio

from mcp.tools import TOOL_REGISTRY, list_tools

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


class MCPToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class MCPToolResponse(BaseModel):
    result: Any
    status: str


@router.post("/call_tool", response_model=MCPToolResponse)
async def call_mcp_tool(request: MCPToolRequest):
    """
    Call an MCP tool via HTTP API.
    
    Example:
        POST /api/v1/mcp/call_tool
        {
            "tool_name": "get_sales_domain_hints",
            "parameters": {"query": "revenue by region"}
        }
    """
    if request.tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found")
    
    try:
        tool_func = TOOL_REGISTRY[request.tool_name]
        result = await tool_func(**request.parameters)
        
        return MCPToolResponse(
            result=result,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_mcp_tools():
    """List all available MCP tools"""
    return {
        "tools": list_tools(),
        "count": len(list_tools())
    }


@router.get("/health")
async def mcp_health():
    """Check MCP tools health"""
    from mcp.tools import health_check
    return await health_check()
```

#### Step 3.2: Register Router in main.py (30 mins)

Edit `backend/main.py`:

```python
# Add import
from routes import chatbot, mcp_endpoint  # Add mcp_endpoint

# Register router
app.include_router(chatbot.router)
app.include_router(mcp_endpoint.router)  # Add this line
```

#### Step 3.3: Test HTTP Endpoints (1 hour)

```bash
# Start FastAPI
cd /home/kiran/Documents/planalytics-genai-solution/backend
python -m uvicorn main:app --reload

# Test list tools
curl http://localhost:8000/api/v1/mcp/tools

# Test health check
curl http://localhost:8000/api/v1/mcp/health

# Test tool call
curl -X POST http://localhost:8000/api/v1/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_sales_domain_hints",
    "parameters": {"query": "revenue by region"}
  }'
```

#### Step 3.4: Update Frontend to Use MCP Tools (2.5 hours)

Create `frontend/lib/mcp-client.ts`:

```typescript
/**
 * MCP Tools Client
 */

export interface MCPToolRequest {
  tool_name: string;
  parameters: Record<string, any>;
}

export interface MCPToolResponse {
  result: any;
  status: string;
}

class MCPClient {
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:8000/api/v1/mcp') {
    this.baseURL = baseURL;
  }

  async callTool(toolName: string, parameters: Record<string, any>): Promise<MCPToolResponse> {
    const response = await fetch(`${this.baseURL}/call_tool`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_name: toolName, parameters })
    });

    if (!response.ok) {
      throw new Error(`Tool call failed: ${response.statusText}`);
    }

    return response.json();
  }

  async listTools(): Promise<string[]> {
    const response = await fetch(`${this.baseURL}/tools`);
    const data = await response.json();
    return data.tools;
  }

  async healthCheck(): Promise<any> {
    const response = await fetch(`${this.baseURL}/health`);
    return response.json();
  }
}

export const mcpClient = new MCPClient();
```

---

### Day 4: Testing & Documentation (8 hours)

#### Step 4.1: Comprehensive Testing (4 hours)

Create `backend/tests/test_mcp_integration.py`:

```python
"""
Integration tests for MCP tools
"""
import pytest
import asyncio
from mcp.tools import *


@pytest.mark.asyncio
async def test_domain_expert_tools():
    """Test all domain expert tools"""
    # Sales
    result = await get_sales_domain_hints("revenue by region")
    assert result["agent"] == "SalesAgent"
    assert "formulas" in result
    
    # WDD
    result = await get_wdd_domain_hints("weather impact")
    assert result["agent"] == "MetricsAgent"
    
    # Weather
    result = await get_weather_domain_hints("heatwave")
    assert result["agent"] == "WeatherAgent"
    
    # Events
    result = await get_events_domain_hints("holiday sales")
    assert result["agent"] == "EventsAgent"
    
    # Inventory
    result = await get_inventory_domain_hints("stockout risk")
    assert result["agent"] == "InventoryAgent"
    
    # Location
    result = await get_location_domain_hints("by region")
    assert result["agent"] == "LocationAgent"


@pytest.mark.asyncio
async def test_utility_tools():
    """Test utility tools"""
    # Date context
    result = await get_current_date_context()
    assert "current_weekend" in result
    assert result["current_weekend"] == "2025-11-08"
    
    # Schema
    result = await get_database_schema()
    assert "tables" in result
    assert len(result["tables"]) == 11
    
    # Health
    result = await health_check()
    assert "postgresql" in result
    assert "azure_search" in result
    assert "gremlin" in result


@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test complete workflow"""
    # 1. Resolve entities
    entities = await resolve_entities("Ice Cream sales in Miami")
    assert len(entities["products"]) > 0
    assert len(entities["locations"]) > 0
    
    # 2. Get domain hints
    sales_hints = await get_sales_domain_hints("sales", entities)
    location_hints = await get_location_domain_hints("Miami", entities)
    
    # 3. Execute SQL
    result = await execute_sql_with_domain_hints(
        query="Ice Cream sales in Miami last week",
        context=entities,
        domain_hints=[sales_hints, location_hints]
    )
    
    assert result["status"] in ["success", "no_data"]
    assert "sql_query" in result
    
    # 4. Generate chart if data
    if result["status"] == "success" and result.get("data"):
        chart = await generate_chart_config(result, "ColumnChart")
        assert "chartType" in chart


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

Run tests:
```bash
cd /home/kiran/Documents/planalytics-genai-solution/backend
pytest tests/test_mcp_integration.py -v
```

#### Step 4.2: Documentation (2 hours)

Create `backend/mcp/MCP_SETUP.md`:

```markdown
# MCP Setup Guide

## Installation

1. Install MCP SDK:
   ```bash
   pip install mcp
   ```

2. Start MCP server:
   ```bash
   python -m backend.mcp.server
   ```

3. Configure Claude Desktop:
   - Copy `config.json` to Claude config directory
   - Restart Claude Desktop
   - Verify tools appear

## Usage

### In Claude Desktop

```
User: "What products need replenishment?"
Claude: [Automatically calls relevant tools]
```

### Via HTTP API

```bash
curl -X POST http://localhost:8000/api/v1/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "health_check", "parameters": {}}'
```

### In Python

```python
from mcp.tools import health_check
import asyncio

result = asyncio.run(health_check())
print(result)
```
```

#### Step 4.3: Performance Testing (1 hour)

```python
# Test concurrent requests
import asyncio
from mcp.tools import *

async def stress_test():
    tasks = [
        get_sales_domain_hints(f"query {i}")
        for i in range(100)
    ]
    results = await asyncio.gather(*tasks)
    print(f"Completed {len(results)} concurrent requests")

asyncio.run(stress_test())
```

#### Step 4.4: Final Validation (1 hour)

**Checklist:**
- [ ] MCP server starts without errors
- [ ] All 13 tools callable
- [ ] Claude Desktop integration works
- [ ] HTTP endpoints functional
- [ ] Tests passing
- [ ] Documentation complete
- [ ] No regressions in existing functionality

---

## 📊 Deliverables

When you're done, you should have:

1. ✅ Working MCP server (`server.py`)
2. ✅ Claude Desktop integration (config installed)
3. ✅ HTTP endpoints (`mcp_endpoint.py`)
4. ✅ Test suite passing
5. ✅ Documentation (MCP_SETUP.md)
6. ✅ Demo video/screenshots

---

## 🤝 Coordination with Developer A

### What Developer A Gave You

- ✅ `tools.py` with 13 working tools
- ✅ `schemas.py` with type definitions
- ✅ Test results proving tools work

### What You're Building On Top

```
Developer A's Work         Your Work
     (tools.py)     →     (server.py + integrations)
         │                        │
         ├─ Tool definitions      ├─ MCP server
         ├─ Error handling        ├─ Claude Desktop config
         ├─ Logging               ├─ HTTP endpoints
         └─ Tests                 └─ Integration tests
```

---

## 🆘 Troubleshooting

### Issue: MCP SDK Import Error

```bash
# Solution
pip install mcp --upgrade
```

### Issue: Tools Not Appearing in Claude

```bash
# Check config location
cat ~/.config/Claude/claude_desktop_config.json

# Restart Claude Desktop completely
killall Claude
open -a Claude  # Mac
claude  # Linux
```

### Issue: Database Connection Errors

```python
# Test database connection
from database.postgres_db import get_db
from sqlalchemy import text

with get_db() as db:
    result = db.execute(text("SELECT 1"))
    print("✅ Database OK")
```

---

## 🎯 Success Criteria

Your implementation is complete when:

1. ✅ Server starts: `python -m mcp.server` runs without errors
2. ✅ Tools work: All 13 tools callable via MCP
3. ✅ Claude works: Can call tools from Claude Desktop
4. ✅ HTTP works: Endpoints respond correctly
5. ✅ Tests pass: 100% test success rate
6. ✅ No regressions: Existing chat endpoint still works

---

## 🚀 You're Done When...

Run this final check:

```bash
cd /home/kiran/Documents/planalytics-genai-solution/backend

# 1. Server starts
python -m mcp.server &
SERVER_PID=$!
sleep 5
kill $SERVER_PID

# 2. Tests pass
pytest tests/test_mcp_integration.py -v

# 3. HTTP endpoints work
python -m uvicorn main:app --reload &
APP_PID=$!
sleep 5
curl http://localhost:8000/api/v1/mcp/tools
kill $APP_PID

# 4. Existing functionality works
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

**If all checks pass** → ✅ **YOU'RE DONE!** 🎉

---

Good luck, Developer B! You've got this! 💪
