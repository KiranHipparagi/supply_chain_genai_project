"""Context Resolver Service - Combines Azure Search entity resolution with Gremlin graph expansion"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from database.azure_search import azure_search
from database.gremlin_db import gremlin_conn
from core.logger import logger

# Static current date context for demo data (November 8, 2025)
CURRENT_WEEKEND_DATE = datetime(2025, 11, 8)
CURRENT_WEEK_END = "2025-11-08"


class ContextResolver:
    """
    Hybrid context resolution using Azure AI Search + Gremlin Knowledge Graph
    
    Workflow:
    1. Azure Search: Resolve vague terms to exact IDs (e.g., "Pepsi" → product_id)
    2. Gremlin Graph: Expand context via relationships (e.g., find all products in same category)
    3. Return enriched context for SQL generation
    
    Date Context:
    - Current Weekend: November 8, 2025 (static for demo data)
    - Next Week: November 15, 2025
    - Last Week: November 1, 2025
    - Next Month: December 2025
    - Last Month: October 2025
    """
    
    def __init__(self):
        self.search = azure_search
        self.graph = gremlin_conn
        # Static date context
        self.current_date = CURRENT_WEEKEND_DATE
        self.current_week_end = CURRENT_WEEK_END
    
    def resolve_query_context(self, user_query: str) -> Dict[str, Any]:
        """
        Main entry point: Resolve full context from natural language query
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            {
                "products": {
                    "resolved": [...],  # From Azure Search
                    "expanded": [...]   # From Gremlin graph
                },
                "locations": {
                    "resolved": [...],
                    "expanded": [...]
                },
                "dates": {
                    "resolved": [...],
                    "date_range": (start, end)
                },
                "events": {
                    "resolved": [...],
                    "related_events": [...]
                },
                "metadata": {
                    "sales_coverage": [...],
                    "weather_coverage": [...],
                    "available_metrics": [...]
                }
            }
        """
        print("\n" + "="*80)
        print("🔎 STEP 1: CONTEXT RESOLUTION - Starting RAG Pipeline")
        print("="*80)
        print(f"📝 User Query: {user_query}")
        logger.info(f"🔍 Resolving context for query: {user_query}")
        
        # Step 1: Entity resolution via Azure Search
        print("\n🔵 STEP 1.1: Azure AI Search - Entity Resolution")
        print("-" * 80)
        entities = self.search.resolve_entities(user_query)
        
        # Detailed printing of resolved entities
        print(f"✅ Entities found:")
        if entities.get('products'):
            print(f"   • Products ({len(entities['products'])}): {[p.get('product', p.get('product_name', 'Unknown')) for p in entities['products'][:5]]}" + (f" ... (+{len(entities['products'])-5} more)" if len(entities['products']) > 5 else ""))
        else:
            print("   • Products: None")
            
        if entities.get('locations'):
            print(f"   • Locations ({len(entities['locations'])}): {[l.get('location', l.get('store_name', 'Unknown')) for l in entities['locations'][:5]]}" + (f" ... (+{len(entities['locations'])-5} more)" if len(entities['locations']) > 5 else ""))
        else:
            print("   • Locations: None")
            
        if entities.get('events'):
            print(f"   • Events ({len(entities['events'])}): {[e.get('event', e.get('event_name', 'Unknown')) for e in entities['events'][:5]]}" + (f" ... (+{len(entities['events'])-5} more)" if len(entities['events']) > 5 else ""))
        else:
            print("   • Events: None")
            
        if entities.get('dates'):
            print(f"   • Dates ({len(entities['dates'])}): {[d.get('date') for d in entities['dates'][:5]]}" + (f" ... (+{len(entities['dates'])-5} more)" if len(entities['dates']) > 5 else ""))
        else:
            print("   • Dates: None")
        
        # Step 2: Context expansion via Gremlin
        print("\n🟢 STEP 1.2: Gremlin Knowledge Graph - Context Expansion")
        print("-" * 80)
        expanded_context = self._expand_context_via_graph(entities)
        
        # Detailed printing of expanded context
        print(f"✅ Graph expansion complete:")
        if expanded_context.get('expanded_products'):
            print(f"   • Expanded Products ({len(expanded_context['expanded_products'])}): {[p.get('product_name') for p in expanded_context['expanded_products'][:5]]}" + (f" ... (+{len(expanded_context['expanded_products'])-5} more)" if len(expanded_context['expanded_products']) > 5 else ""))
        else:
            print("   • Expanded Products: None")
            
        if expanded_context.get('expanded_locations'):
            print(f"   • Expanded Locations ({len(expanded_context['expanded_locations'])}): {[l.get('store_name') for l in expanded_context['expanded_locations'][:5]]}" + (f" ... (+{len(expanded_context['expanded_locations'])-5} more)" if len(expanded_context['expanded_locations']) > 5 else ""))
        else:
            print("   • Expanded Locations: None")
        
        # Step 3: Get metadata context
        metadata = self.search.get_schema_context(user_query)
        
        # Step 4: Combine everything
        full_context = {
            "products": {
                "resolved": entities.get("products", []),
                "expanded": expanded_context.get("expanded_products", [])
            },
            "locations": {
                "resolved": entities.get("locations", []),
                "expanded": expanded_context.get("expanded_locations", [])
            },
            "dates": {
                "resolved": entities.get("dates", []),
                "date_range": self._extract_date_range(entities.get("dates", []))
            },
            "events": {
                "resolved": entities.get("events", []),
                "related_events": expanded_context.get("related_events", [])
            },
            "metadata": metadata
        }
        
        logger.info(f"✅ Context resolved successfully")
        return full_context
    
    def _expand_context_via_graph(self, entities: Dict[str, List]) -> Dict[str, Any]:
        """Expand entity context using Gremlin knowledge graph relationships"""
        print("  🌐 Querying Gremlin Graph Database...")
        if not self.graph.ensure_connected():
            logger.warning("⚠️ Gremlin unavailable - skipping graph expansion (system will use Azure Search only)")
            print("  ⚠️  Gremlin Graph unavailable - using Azure Search context only")
            return {
                "expanded_products": [],
                "expanded_locations": [],
                "related_events": []
            }
        
        expanded = {}
        
        # Expand products via category hierarchy
        product_ids = [p.get("id") for p in entities.get("products", []) if p.get("id")]
        if product_ids:
            print(f"  📦 Expanding product context for IDs: {product_ids[:3]}...")
            expanded["expanded_products"] = self.graph.expand_product_context(product_ids)
            print(f"  ✅ Found {len(expanded['expanded_products'])} related products via graph traversal")
        else:
            expanded["expanded_products"] = []
        
        # Expand locations via geographic hierarchy
        location_ids = [l.get("id") for l in entities.get("locations", []) if l.get("id")]
        if location_ids:
            print(f"  🏢 Expanding location context for IDs: {location_ids[:3]}...")
            expanded["expanded_locations"] = self.graph.expand_location_context(location_ids)
            print(f"  ✅ Found {len(expanded['expanded_locations'])} related locations via graph traversal")
        else:
            expanded["expanded_locations"] = []
        
        # Find related events
        date_list = [d.get("date") for d in entities.get("dates", []) if d.get("date")]
        if date_list and location_ids:
            expanded["related_events"] = self.graph.find_related_events(location_ids, date_list)
        else:
            expanded["related_events"] = []
        
        return expanded
    
    def _convert_excel_date(self, val: Any) -> Any:
        """Convert Excel serial date to YYYY-MM-DD string"""
        try:
            if isinstance(val, (int, float)):
                return (datetime(1899, 12, 30) + timedelta(days=val)).strftime('%Y-%m-%d')
            elif isinstance(val, str) and val.isdigit():
                return (datetime(1899, 12, 30) + timedelta(days=int(val))).strftime('%Y-%m-%d')
            return val
        except Exception:
            return val

    def _extract_date_range(self, dates: List[Dict]) -> Optional[tuple]:
        """Extract min/max date range from calendar results"""
        if not dates:
            return None
        
        date_values = [self._convert_excel_date(d.get("date")) for d in dates if d.get("date")]
        if not date_values:
            return None
        
        return (min(date_values), max(date_values))
    
    def get_sql_generation_prompt(self, user_query: str, context: Dict[str, Any]) -> str:
        """
        Generate a comprehensive prompt for SQL generation with full context
        
        This replaces the hardcoded schema prompt in database_agent.py
        """
        prompt_parts = []
        
        # Add static date context at the top (CRITICAL for relative date queries)
        prompt_parts.append("=== CURRENT DATE CONTEXT ===")
        prompt_parts.append(f"Current Weekend (Week End Date): {self.current_week_end} (November 8, 2025)")
        prompt_parts.append("- 'This week' or 'current week' = end_date '2025-11-08'")
        prompt_parts.append("- 'Next week' or 'NW' = end_date '2025-11-15'")
        prompt_parts.append("- 'Last week' or 'LW' = end_date '2025-11-01'")
        prompt_parts.append("- 'Next month' or 'NM' = December 2025 → Use: c.month = 'December' AND c.year = 2025")
        prompt_parts.append("- 'Last month' or 'LM' = October 2025 → Use: c.month = 'October' AND c.year = 2025")
        prompt_parts.append("- 'Last year' or 'LY' = 2024")
        prompt_parts.append("- 'Next 2 weeks' = end_dates '2025-11-15' and '2025-11-22'")
        prompt_parts.append("- 'Last 6 weeks' = 6 weeks ending before '2025-11-08'")
        prompt_parts.append("- CRITICAL: calendar.month column is STRING ('January', 'December'), NOT integer!\n")
        
        # User query
        prompt_parts.append(f"User Query: {user_query}\n")
        
        # Products context
        products = context.get("products", {})
        if products.get("resolved"):
            # CRITICAL: Detect if user is asking about CATEGORY/DEPARTMENT or SPECIFIC PRODUCTS
            # Azure Search returns product matches, but we need to determine user's intent
            product_info = []
            product_names = []
            categories = set()
            departments = set()
            
            for p in products["resolved"][:10]:  # Check all returned products
                name = p.get("product", p.get("product_name", p.get("id", "Unknown")))
                cat = p.get("category", "Unknown")
                dept = p.get("dept", "Unknown")
                product_info.append(f"{name} (Dept: {dept}, Category: {cat})")
                product_names.append(name)
                categories.add(cat)
                departments.add(dept)
            
            product_ids = [p.get("product_id", p.get("id")) for p in products["resolved"][:10]]
            
            prompt_parts.append(f"Relevant Products: {', '.join(product_info)}")
            prompt_parts.append(f"Product Names Found: {product_names}")
            prompt_parts.append(f"Categories Found: {list(categories)}")
            prompt_parts.append(f"Departments Found: {list(departments)}")
            prompt_parts.append(f"Product IDs: {product_ids}")
            
            prompt_parts.append("\n🚨🚨 CRITICAL PRODUCT FILTERING RULES - READ CAREFULLY:")
            prompt_parts.append("")
            prompt_parts.append("=== STEP 1: IDENTIFY USER'S INTENT ===")
            prompt_parts.append("Analyze the User Query above and determine what level the user is asking about:")
            prompt_parts.append("")
            prompt_parts.append("📦 OPTION A: User mentions a CATEGORY or DEPARTMENT")
            prompt_parts.append("   Keywords in query: 'QSR', 'Perishable', 'Fast Food', 'Grocery', 'Beverages', 'Dairy', etc.")
            prompt_parts.append("   Examples:")
            prompt_parts.append("   - 'Which QSR products...' → User is asking about CATEGORY = 'QSR'")
            prompt_parts.append("   - 'How many products in QSR category?' → CATEGORY = 'QSR'")
            prompt_parts.append("   - 'Perishable items' → CATEGORY = 'Perishable'")
            prompt_parts.append("   - 'Fast Food department' → DEPT = 'Fast Food'")
            prompt_parts.append("   - 'Grocery products' → DEPT = 'Grocery'")
            prompt_parts.append("")
            prompt_parts.append("📦 OPTION B: User mentions SPECIFIC PRODUCT NAMES")
            prompt_parts.append("   Keywords in query: 'Hamburgers', 'Milk', 'Sandwiches', 'Eggs', 'Coffee', etc.")
            prompt_parts.append("   Examples:")
            prompt_parts.append("   - 'Sandwiches and Salads' → User is asking about specific products")
            prompt_parts.append("   - 'How did Hamburgers perform?' → Specific product = 'Hamburgers'")
            prompt_parts.append("   - 'Milk sales' → Specific product = 'Milk'")
            prompt_parts.append("")
            prompt_parts.append("=== STEP 2: APPLY CORRECT SQL FILTER ===")
            prompt_parts.append("")
            prompt_parts.append("✅ IF USER ASKS ABOUT CATEGORY (Option A):")
            prompt_parts.append("   → Filter on: WHERE ph.category = 'category_name'")
            prompt_parts.append("   → DO NOT filter on specific product names!")
            prompt_parts.append("   → Let the database return ALL products in that category")
            prompt_parts.append("   Examples:")
            prompt_parts.append("   - 'QSR products' → WHERE ph.category = 'QSR'")
            prompt_parts.append("   - 'Perishable items' → WHERE ph.category = 'Perishable'")
            prompt_parts.append("   - 'How many QSR products?' → SELECT COUNT(*) FROM product_hierarchy WHERE category = 'QSR'")
            prompt_parts.append("")
            prompt_parts.append("✅ IF USER ASKS ABOUT DEPARTMENT (Option A):")
            prompt_parts.append("   → Filter on: WHERE ph.dept = 'dept_name'")
            prompt_parts.append("   → DO NOT filter on specific product names!")
            prompt_parts.append("   Examples:")
            prompt_parts.append("   - 'Fast Food products' → WHERE ph.dept = 'Fast Food'")
            prompt_parts.append("   - 'Grocery department' → WHERE ph.dept = 'Grocery'")
            prompt_parts.append("")
            prompt_parts.append("✅ IF USER ASKS ABOUT SPECIFIC PRODUCTS (Option B):")
            prompt_parts.append("   → Filter on: WHERE ph.product IN ('product1', 'product2', ...)")
            prompt_parts.append("   → ONLY include products user explicitly mentioned in the query")
            prompt_parts.append("   → DO NOT include all products from Azure Search results!")
            prompt_parts.append("   Examples:")
            prompt_parts.append("   - 'Sandwiches' → WHERE ph.product = 'Sandwiches'")
            prompt_parts.append("   - 'Sandwiches and Salads' → WHERE ph.product IN ('Sandwiches', 'Salads')")
            prompt_parts.append("   - 'Milk, Eggs, and Bacon' → WHERE ph.product IN ('Milk', 'Eggs', 'Bacon')")
            prompt_parts.append("")
            prompt_parts.append("=== STEP 3: EXAMPLES OF CORRECT vs WRONG SQL ===")
            prompt_parts.append("")
            prompt_parts.append("❌ WRONG - User asks 'QSR products' but you filter on specific products:")
            prompt_parts.append("   SELECT ... WHERE ph.product IN ('Sandwiches', 'Salads', 'Chicken')  ← WRONG!")
            prompt_parts.append("   Problem: Misses Hamburgers, Pizza, Coffee & Tea, Desserts, Smoothies!")
            prompt_parts.append("")
            prompt_parts.append("✅ CORRECT - User asks 'QSR products':")
            prompt_parts.append("   SELECT ... WHERE ph.category = 'QSR'  ← CORRECT!")
            prompt_parts.append("   Returns: ALL 8 QSR products (Hamburgers, Chicken, Coffee & Tea, Desserts, Sandwiches, Smoothies, Salads, Pizza)")
            prompt_parts.append("")
            prompt_parts.append("❌ WRONG - User asks 'How many products in QSR category?':")
            prompt_parts.append("   SELECT COUNT(*) ... WHERE ph.product IN ('Sandwiches', 'Salads')  ← WRONG!")
            prompt_parts.append("   Result: Returns 2 instead of 8")
            prompt_parts.append("")
            prompt_parts.append("✅ CORRECT - User asks 'How many products in QSR category?':")
            prompt_parts.append("   SELECT COUNT(DISTINCT ph.product) FROM product_hierarchy WHERE ph.category = 'QSR'  ← CORRECT!")
            prompt_parts.append("   Result: Returns 8 (all QSR products)")
            prompt_parts.append("")
            prompt_parts.append("❌ WRONG - User asks 'Perishable items':")
            prompt_parts.append("   SELECT ... WHERE ph.product IN ('Milk', 'Eggs')  ← WRONG! Misses Bacon")
            prompt_parts.append("")
            prompt_parts.append("✅ CORRECT - User asks 'Perishable items':")
            prompt_parts.append("   SELECT ... WHERE ph.category = 'Perishable'  ← CORRECT!")
            prompt_parts.append("   OR join with perishable table: JOIN perishable p ON ph.product = p.product")
            prompt_parts.append("")
            prompt_parts.append("❌ WRONG - User asks 'Sandwiches performance' but you filter on category:")
            prompt_parts.append("   SELECT ... WHERE ph.category = 'QSR'  ← WRONG! Returns all QSR, not just Sandwiches")
            prompt_parts.append("")
            prompt_parts.append("✅ CORRECT - User asks 'Sandwiches performance':")
            prompt_parts.append("   SELECT ... WHERE ph.product = 'Sandwiches'  ← CORRECT!")
            prompt_parts.append("")
            prompt_parts.append("=== SPECIAL CASES ===")
            prompt_parts.append("")
            prompt_parts.append("🔍 CASE 1: User says 'QSR products like Sandwiches and Salads'")
            prompt_parts.append("   → This is asking about SPECIFIC PRODUCTS, not whole category")
            prompt_parts.append("   → Use: WHERE ph.product IN ('Sandwiches', 'Salads')")
            prompt_parts.append("")
            prompt_parts.append("🔍 CASE 2: User says 'All QSR products'")
            prompt_parts.append("   → This is asking about ENTIRE CATEGORY")
            prompt_parts.append("   → Use: WHERE ph.category = 'QSR'")
            prompt_parts.append("")
            prompt_parts.append("🔍 CASE 3: User says 'What department are perishable items in?'")
            prompt_parts.append("   → This is asking about CATEGORY = 'Perishable'")
            prompt_parts.append("   → Use: SELECT ph.dept FROM product_hierarchy WHERE ph.category = 'Perishable' GROUP BY ph.dept")
            prompt_parts.append("   → OR: JOIN perishable table to show all perishable products")
            prompt_parts.append("")
            prompt_parts.append("🔍 CASE 4: Counting products in a category")
            prompt_parts.append("   → User asks: 'How many products in QSR?', 'Count of Perishable items', etc.")
            prompt_parts.append("   → Use: SELECT COUNT(DISTINCT ph.product) FROM product_hierarchy WHERE ph.category = 'category_name'")
            prompt_parts.append("   → DO NOT filter on specific product names!")
            prompt_parts.append("")
            prompt_parts.append("=== DECISION TREE ===")
            prompt_parts.append("")
            prompt_parts.append("1. Check User Query for category/department keywords ('QSR', 'Perishable', 'Fast Food', 'Grocery')")
            prompt_parts.append("   → YES → Use: WHERE ph.category = '...' OR WHERE ph.dept = '...'")
            prompt_parts.append("   → NO → Continue to step 2")
            prompt_parts.append("")
            prompt_parts.append("2. Check if user mentioned specific product names ('Hamburgers', 'Milk', 'Sandwiches')")
            prompt_parts.append("   → YES → Use: WHERE ph.product IN ('product1', 'product2', ...)")
            prompt_parts.append("   → Count how many products user mentioned, use ONLY those")
            prompt_parts.append("")
            prompt_parts.append("3. If unclear, prefer CATEGORY/DEPARTMENT filter over specific products")
            prompt_parts.append("   → It's better to return all products in a category than to miss some")
            prompt_parts.append("")
            prompt_parts.append(f"Available categories in this query: {list(categories)}")
            prompt_parts.append(f"Available departments in this query: {list(departments)}")
            prompt_parts.append(f"Available products in this query: {product_names}\n")
        
        if products.get("expanded"):
            # DO NOT include expanded products - user wants ONLY what they mentioned!
            # Expansion can add unwanted products like 'Salads' when user only asked for 'Sandwiches'
            pass  # Intentionally disabled to prevent over-filtering
        
        # Locations context
        locations = context.get("locations", {})
        if locations.get("resolved"):
            # Use 'location' field (fallback to 'store_name' or 'id')
            location_names = [l.get("location", l.get("store_name", l.get("id", "Unknown"))) for l in locations["resolved"][:5]]
            location_ids = [l.get("id") for l in locations["resolved"][:20]]
            prompt_parts.append(f"Relevant Locations: {', '.join(str(x) for x in location_names)}")
            prompt_parts.append(f"Store IDs to filter: {location_ids}\n")
        
        if locations.get("expanded"):
            expanded_ids = [l.get("store_id") for l in locations["expanded"][:50]]
            prompt_parts.append(f"Related Locations (same region/market): {len(expanded_ids)} stores")
            prompt_parts.append(f"Expanded Store IDs: {expanded_ids}\n")
        
        # Date context
        dates = context.get("dates", {})
        if dates.get("date_range"):
            start_date, end_date = dates["date_range"]
            prompt_parts.append(f"Date Range: {start_date} to {end_date}\n")
        elif dates.get("resolved"):
            date_samples = [d.get("date") for d in dates["resolved"][:5]]
            prompt_parts.append(f"Relevant Dates: {date_samples}\n")
        
        # Events context
        events = context.get("events", {})
        if events.get("resolved"):
            # Use 'event' field (fallback to 'event_name')
            event_names = [e.get("event", e.get("event_name", "Unknown Event")) for e in events["resolved"][:5]]
            prompt_parts.append(f"Relevant Events: {', '.join(str(x) for x in event_names)}\n")
        
        # Database schema (dynamic based on query needs)
        prompt_parts.append("\nAvailable Database Tables:")
        prompt_parts.append("""
=== QUERY TYPE DETECTION (CRITICAL!) ===
FIRST, carefully determine which type of data the user needs:

**TYPE 1: SALES PERFORMANCE ANALYSIS** → Use 'sales' table
   Primary Keywords: "sales", "sold", "revenue", "perform", "performance", "growing", "fastest growing", 
                     "units sold", "sales amount", "traffic", "transactions", "change in sales"
   Questions like: "How did X perform?", "sales of X changed", "fastest growing demand", "units sold"
   Example: "How did Smoothies perform in Charlotte during heatwave weeks?"
   SQL Strategy: Use sales table, join with product_hierarchy, location, calendar

**TYPE 2: WDD + SALES COMBINED ANALYSIS** → Join 'metrics' AND 'sales' tables
   Keywords: "weather affected sales", "weather affect demand", "weather impact/impacts on", "due to weather", 
             "weather impact on sales", "weather-driven sales", "compared to weather", "because of weather", 
             "weather and sales", "based on weather", "based on the weather", "weather + performance/YoY"
   Questions like: "How much was due to weather?", "weather impacts on traffic", "weather affect demand",
                   "based on weather, what products had best performance"
   Example: "Sandwich sales were down. How much was due to weather?"
   Example: "How much did weather affect demand in Apparel this summer?"
   Example: "Based on the weather, what grocery products had the best year-over-year performance?"
   SQL Strategy: Join metrics and sales tables to compare WDD trend vs actual sales performance
   
**TYPE 3: WEATHER-DRIVEN DEMAND ONLY** → Use 'metrics' table only
   Keywords: "WDD", "demand forecast", "weather-driven demand", "seasonal demand", "weather trend"
   Questions like: "What's the weather-driven demand trend?"
   Example: "Show WDD for ice cream this summer"
   SQL Strategy: Use metrics table for trend analysis (no sales join needed)

**TYPE 4: INVENTORY/BATCH TRACKING** → Use 'batches' + 'batch_stock_tracking' tables
   Keywords: "inventory", "stock", "batch", "expiry", "expiring", "stock level", "stock movements"
   Example: "What batches are expiring next week?"
   
**TYPE 5: SPOILAGE/WASTE** → Use 'spoilage_report' table
   Keywords: "spoilage", "waste", "spoiled", "expired products", "loss"
   Example: "Which stores have highest spoilage?"

**TYPE 6: EVENT-BASED QUERIES** → Use 'events' table + 'sales' table
   Keywords: "festival", "concert", "game", "holiday", "event", specific event names
   CRITICAL: Search BOTH event AND event_type columns!
   Example WHERE: (e.event ILIKE '%music%' OR e.event_type ILIKE '%music%' OR e.event_type ILIKE '%festival%')
   Example: "Music festival in Nashville" → Search event column AND event_type column

**TYPE 6: EVENT-BASED ANALYSIS** → Use 'events' table joined with sales or metrics
   Keywords: "event", "festival", "holiday", "concert", "game", "football", "music festival"
   Example: "What sold most during the music festival?"
   SQL Strategy: Find events, then join with sales for actual performance

=== DECISION TREE ===
1. Does query mention "sales", "sold", "perform", "revenue", "growing", "traffic"? → TYPE 1 or TYPE 2
   - If ALSO mentions "weather affect", "due to weather" → TYPE 2 (WDD + SALES combined)
   - If NO weather causation mentioned → TYPE 1 (SALES only)
   
2. Does query mention "weather" without "sales" context? → TYPE 3 (WDD only)

3. Does query mention "inventory", "stock", "batch"? → TYPE 4

4. Does query mention "spoilage", "waste"? → TYPE 5

5. Does query mention event names or types? → TYPE 6

=== TABLE SCHEMAS ===

METRICS TABLE (Weekly WDD TREND data - NOT actual sales numbers!):
================================================================================
CRITICAL UNDERSTANDING: The metrics table contains TREND VALUES for analyzing 
weather-driven demand spikes or dips. These numbers are NOT actual sales/demand!

- metrics (id, product, location, end_date, metric, metric_nrm, metric_ly)
  * product = Product name (e.g., 'Hamburgers', 'Coffee & Tea', 'Milk')
  * location = Store ID (e.g., 'ST0050', 'ST2900')
  * end_date = Week ending date (joins with calendar.end_date)
  * metric = WDD (Weather Driven Demand) TREND VALUE - weather-adjusted
  * metric_nrm = Normal demand TREND (baseline, no weather impact) - FOR FUTURE ≤4 weeks
  * metric_ly = Last Year demand TREND - FOR PAST/YoY/>4 weeks comparisons
  
  IMPORTANT: metric numbers are NOT actual demand - they're TREND VALUES!
  USE metrics table to calculate WDD PERCENTAGE, then apply to actual sales.
  
  WDD FORMULA SELECTION RULES:
  - Short-term (≤4 weeks, FUTURE): (metric - metric_nrm) / metric_nrm * 100
  - Long-term (>4 weeks) OR Historical/YoY: (metric - metric_ly) / metric_ly * 100
  
  USE FOR: Weather impact analysis, WDD percentage calculations, demand trend forecasting

SALES TABLE (Actual transaction-level sales data - REAL PERFORMANCE):
- sales (id, batch_id, store_code, product_code, transaction_date, sales_units, sales_amount, discount_amount, total_amount)
  * batch_id = Links to batches.batch_id
  * store_code = Store ID (links to location.location) e.g., 'ST0050'
  * product_code = Product ID INTEGER (links to product_hierarchy.product_id)
  * transaction_date = Date of sale (DATE type)
  * sales_units = Number of units sold (INTEGER) ← ACTUAL UNITS SOLD
  * sales_amount = Gross sales amount before discount (NUMERIC)
  * discount_amount = Discount applied (NUMERIC)
  * total_amount = Net sales after discount (NUMERIC)
  * REVENUE CALCULATION: SUM(sales_units * total_amount) ← CRITICAL FORMULA!
  * USE THIS for: actual revenue, units sold, sales performance, "how did X perform" questions

BATCHES TABLE (Inventory batches with expiry tracking):
- batches (id, batch_id, store_code, product_code, transaction_date, expiry_date, unit_price, total_value, received_qty, mfg_date, week_end_date, stock_received, stock_at_week_start, stock_at_week_end)
  * batch_id = Unique batch identifier (PRIMARY KEY for batch queries)
  * store_code = Store ID (links to location.location)
  * product_code = Product ID INTEGER (links to product_hierarchy.product_id)
  * transaction_date = Date batch was received
  * expiry_date = Expiration date (DATE) - use for expiry analysis!
  * mfg_date = Manufacturing date
  * received_qty = Quantity received in batch
  * stock_at_week_start = Opening stock for the week
  * stock_at_week_end = Closing stock for the week
  * week_end_date = Week ending date (joins with calendar.end_date)
  * USE THIS for: inventory levels, expiry tracking, batch lifecycle

BATCH_STOCK_TRACKING TABLE (Inventory movements):
- batch_stock_tracking (record_id, batch_id, store_code, product_code, transaction_type, transaction_date, qty_change, stock_after_transaction, unit_price)
  * record_id = Unique record ID
  * batch_id = Links to batches.batch_id
  * store_code = Store ID (links to location.location)
  * product_code = Product ID INTEGER (links to product_hierarchy.product_id)
  * transaction_type = Movement type:
    - 'SALE' = Units sold from this batch
    - 'TRANSFER_IN' = Stock transferred in
    - 'ADJUSTMENT' = Inventory adjustment
    - 'SPOILAGE' = Stock spoiled/wasted
    - 'RETURN' = Customer returns
  * transaction_date = Date of movement (DATE type)
  * qty_change = Quantity changed (positive=in, negative=out)
  * stock_after_transaction = Running balance after this transaction
  * USE THIS for: stock movement analysis, transfer tracking

SPOILAGE_REPORT TABLE (Waste tracking):
- spoilage_report (id, batch_id, store_code, product_code, qty, spoilage_qty, spoilage_pct, spoilage_case)
  * batch_id = Links to batches.batch_id
  * store_code = Store ID (links to location.location)
  * product_code = Product ID INTEGER (links to product_hierarchy.product_id)
  * qty = Original quantity in batch
  * spoilage_qty = Quantity spoiled (INTEGER)
  * spoilage_pct = Spoilage percentage (0-100, NUMERIC)
  * spoilage_case = Severity level (INTEGER: 1=Low 0-5%, 2=Medium 5-10%, 3=High 10-20%, 4=Critical 20%+)
  * USE THIS for: spoilage analysis, waste patterns, loss tracking

EVENTS TABLE (for event-based analysis - IMPORTANT for festival/holiday queries):
- events (id, event, event_type, event_date, store_id, region, market, state)
  * event = Event name (e.g., 'Memorial Day', 'Black Friday', 'Music Festival')
  * event_type = Category (e.g., 'National Holiday', 'Sporting Event', 'Concert', 'Festival')
  * event_date = Date of event (DATE type)
  * store_id = Affected store (links to location.location)
  * region, market, state = Location info
  * USE THIS for: finding events near stores, event impact on sales

WEEKLY_WEATHER TABLE:
- weekly_weather (id, week_end_date, avg_temp_f, temp_anom_f, tmax_f, tmin_f, 
                  precip_in, precip_anom_in, heatwave_flag, cold_spell_flag, heavy_rain_flag, snow_flag, store_id)
  * week_end_date = Week ending date (joins with calendar.end_date)
  * store_id = Store ID (links to location.location)
  * heatwave_flag, cold_spell_flag, heavy_rain_flag, snow_flag = BOOLEAN weather alerts

LOCATION TABLE:
- location (id, location, region, market, state, latitude, longitude)
  * location = Store ID (PRIMARY KEY, e.g., 'ST6111')
  * region = LOWERCASE: 'northeast', 'southeast', 'midwest', 'west', 'southwest'
  * market = Market area (e.g., 'chicago, il', 'dallas, tx')
  * state = State name lowercase (e.g., 'illinois', 'texas')

PRODUCT_HIERARCHY TABLE (CRITICAL - Supports 3-level hierarchy filtering):
- product_hierarchy (product_id, dept, category, product)
  * product_id = INTEGER PRIMARY KEY (for joining with sales, batches, etc.)
  * dept = Department name (e.g., 'Fast Food', 'Grocery') - HIGHEST LEVEL
  * category = Product category (e.g., 'QSR', 'Perishable', 'Beverages') - MIDDLE LEVEL
  * product = Specific product name (e.g., 'Hamburgers', 'Milk', 'Sandwiches') - LOWEST LEVEL
  
  🔍 HIERARCHICAL FILTERING LOGIC:
  
  Level 1 - DEPARTMENT (Broadest):
    - User mentions: "Fast Food", "Grocery", "Department"
    - SQL: WHERE ph.dept = 'dept_name'
    - Example: "Fast Food products" → WHERE ph.dept = 'Fast Food'
  
  Level 2 - CATEGORY (Middle):
    - User mentions: "QSR", "Perishable", "Beverages", "Category"
    - SQL: WHERE ph.category = 'category_name'
    - Example: "QSR products" → WHERE ph.category = 'QSR'
    - Example: "Perishable items" → WHERE ph.category = 'Perishable'
  
  Level 3 - PRODUCT (Most Specific):
    - User mentions specific names: "Hamburgers", "Milk", "Sandwiches"
    - SQL: WHERE ph.product = 'product_name' OR WHERE ph.product IN ('p1', 'p2')
    - Example: "Sandwiches" → WHERE ph.product = 'Sandwiches'
  
  🚨 CRITICAL EXAMPLES:
  
  ✅ CORRECT - "Which QSR products should perform best?"
     SELECT ph.product FROM product_hierarchy ph WHERE ph.category = 'QSR'
     → Returns: Hamburgers, Chicken, Coffee & Tea, Desserts, Sandwiches, Smoothies, Salads, Pizza (8 products)
  
  ❌ WRONG - "Which QSR products should perform best?"
     SELECT ... WHERE ph.product IN ('Sandwiches', 'Salads', 'Chicken')
     → Missing: Hamburgers, Coffee & Tea, Desserts, Smoothies, Pizza (incomplete!)
  
  ✅ CORRECT - "How many products in QSR category?"
     SELECT COUNT(DISTINCT product) FROM product_hierarchy WHERE category = 'QSR'
     → Returns: 8
  
  ❌ WRONG - "How many products in QSR category?"
     SELECT COUNT(*) WHERE product IN ('Sandwiches', 'Salads')
     → Returns: 2 (should be 8!)
  
  ✅ CORRECT - "What department are perishable items in?"
     SELECT DISTINCT dept FROM product_hierarchy WHERE category = 'Perishable'
     → Returns: 'Grocery'
  
  ❌ WRONG - "What department are perishable items in?"
     SELECT dept WHERE product IN ('Milk', 'Eggs')
     → Misses other perishable products like 'Bacon'!
  
  📊 ACTUAL DATA IN DATABASE:
     Fast Food Department → QSR Category → 8 products:
       - Hamburgers, Chicken, Coffee & Tea, Desserts, Sandwiches, Smoothies, Salads, Pizza
     
     Grocery Department → Perishable Category → 3 products in product_hierarchy:
       - Bacon, Eggs, Milk
     
     (More perishable products like Ice Cream are in the perishable table but not in product_hierarchy)

PERISHABLE TABLE (Extended perishable product details):
- perishable (id, product, perishable_id, min_period, max_period, period_metric, storage)
  * product = Perishable product name (e.g., 'Bacon', 'Eggs', 'Milk', 'Ice Cream')
  * min_period, max_period = Shelf life range as TEXT (e.g., '7', '14', '30') - MUST CAST TO INTEGER!
  * period_metric = Unit of time ('Days', 'Weeks', 'Months')
  * storage = Storage requirements ('Refrigerate', 'Freeze', 'Pantry', etc.)
  
  ⚠️ CRITICAL - SHELF LIFE CALCULATIONS:
  When doing arithmetic with max_period, ALWAYS cast to integer first:
  ✅ CORRECT: CAST(p.max_period AS INTEGER) AS shelf_life_days
  ✅ CORRECT: CAST(p.max_period AS INTEGER) - some_numeric_value
  ❌ WRONG: p.max_period - some_numeric_value  (TEXT - NUMERIC causes error!)
  ❌ WRONG: MAX(p.max_period) AS shelf_life_days  (returns TEXT, not INTEGER!)
  
  🔍 PERISHABLE QUERIES:
  - For complete list: JOIN product_hierarchy WITH perishable table
  - For just hierarchy products: WHERE ph.category = 'Perishable'
  - Example: "What perishable products do we have?"
    SELECT DISTINCT p.product, p.storage, p.max_period, p.period_metric
    FROM perishable p
    → Returns: Bacon, Eggs, Milk, Ice Cream (from perishable table)
  
  - Example: "What department are perishable items in?"
    SELECT DISTINCT ph.dept FROM product_hierarchy ph WHERE ph.category = 'Perishable'
    → Returns: 'Grocery'
  * storage = 'Refrigerate', 'Freeze', 'Pantry'

CALENDAR TABLE (NRF Retail Calendar):
- calendar (id, end_date, year, quarter, month, week, season)
  * end_date = Week ending date (DATE)
  * year = INTEGER (fiscal year)
  * quarter = INTEGER (1-4)
  * month = STRING (FULL NAME: 'January', 'February', etc.) NOT integer!
  * week = NRF retail week number (1-53)
  * season = 'Spring', 'Summer', 'Fall', 'Winter'

⚠️ CRITICAL - CALENDAR DATE FILTERING:
  When filtering by YEAR, QUARTER, or SEASON - use calendar columns directly:
  ✅ CORRECT: WHERE c.year = 2025 OR c.year IN (2023, 2024, 2025)
  ✅ CORRECT: WHERE c.quarter = 3 AND c.year = 2025
  ✅ CORRECT: WHERE c.season = 'Fall' AND c.year = 2025
  ❌ WRONG: WHERE c.year = 2025 AND c.end_date BETWEEN '2025-01-01' AND '2025-12-31'
  
  Why: NRF calendar already has the correct date ranges mapped to years/quarters/seasons!
  You do NOT need to add extra BETWEEN date filters when using calendar.year/quarter/season.
  
  Exception: Only use BETWEEN dates when user specifies exact dates like "March 18 to August 2"

=== JOIN PATTERNS ===
- metrics → location: metrics.location = location.location
- metrics → product_hierarchy: metrics.product = product_hierarchy.product
- metrics → calendar: metrics.end_date = calendar.end_date
- sales → location: sales.store_code = location.location
- sales → product_hierarchy: sales.product_code = product_hierarchy.product_id
- batches → location: batches.store_code = location.location
- batches → product_hierarchy: batches.product_code = product_hierarchy.product_id
- batches → calendar: batches.week_end_date = calendar.end_date
- batch_stock_tracking → batches: batch_stock_tracking.batch_id = batches.batch_id
- spoilage_report → batches: spoilage_report.batch_id = batches.batch_id
- spoilage_report → product_hierarchy: spoilage_report.product_code = product_hierarchy.product_id
- events → location: events.store_id = location.location
- weekly_weather → location: weekly_weather.store_id = location.location

=== EVENT-BASED ANALYSIS APPROACH ===
When user asks about events (festivals, holidays, concerts, games):
1. Find relevant events from events table by name/type/date
2. Get the stores affected (events.store_id)
3. For sales impact: Join with sales table on store_code and nearby transaction_date
4. For demand forecast: Join with metrics on location and end_date
5. Look at historical data from same event last year for comparison

Example: "What products should I stock for a music festival in Nashville?"
1. SELECT * FROM events WHERE event ILIKE '%music%' AND market ILIKE '%nashville%'
2. Find affected stores
3. Join with historical sales data around similar events
4. Identify top-selling products during past events""")
        
        # WDD Formulas section
        prompt_parts.append("""
=== WDD FORMULAS (For metrics table ONLY) ===

CRITICAL: Determine if the query is asking about FUTURE or HISTORICAL/PAST data:

1. FUTURE QUERIES (Next week, next month, next 2 weeks, upcoming period, "this coming"):
   Use: WDD vs Normal (metric vs metric_nrm)
   Formula: (SUM(metric) - SUM(metric_nrm)) / NULLIF(SUM(metric_nrm), 0)
   Keywords: "next", "upcoming", "expected", "forecast", "will be", "coming", "planning for"

2. HISTORICAL/PAST QUERIES (Last week, last month, past 6 weeks, previous period):
   Use: WDD vs Last Year (metric vs metric_ly)
   Formula: (SUM(metric) - SUM(metric_ly)) / NULLIF(SUM(metric_ly), 0)
   Keywords: "last", "past", "previous", "ago", "was", "were", "had"

3. YEAR-OVER-YEAR COMPARISONS (Trend analysis, change over time):
   Use: WDD vs Last Year (metric vs metric_ly)
   Formula: (SUM(metric) - SUM(metric_ly)) / NULLIF(SUM(metric_ly), 0)
   Keywords: "year-over-year", "YoY", "compared to last year", "vs last year", "biggest change"

4. PLANNING QUERIES WITH HISTORICAL CONTEXT ("based on last year", "considering last spring"):
   These queries want BOTH historical data AND current planning:
   - First analyze last year's patterns using metric_ly
   - Then show current year forecast vs historical using metric vs metric_ly
   Example: "Considering the impact of weather last spring, how should we plan for this coming spring?"
   → This needs YoY comparison to show how current forecast differs from last year
   → Use metric vs metric_ly to show year-over-year weather impact differences
   
5. RISK ANALYSIS ("weather-driven risks", "biggest risks"):
   Use: WDD vs Last Year (metric vs metric_ly) 
   A positive % = demand UP vs last year (opportunity)
   A negative % = demand DOWN vs last year (risk if inventory not adjusted)
   Formula: ROUND((SUM(metric) - SUM(metric_ly)) / NULLIF(SUM(metric_ly), 0) * 100, 2) AS yoy_risk_pct

EXAMPLES:
- "next month" → Use metric vs metric_nrm
- "last week" → Use metric vs metric_ly
- "past 6 weeks" → Use metric vs metric_ly
- "biggest change" → Use metric vs metric_ly
- "over the last three weeks" → Use metric vs metric_ly
- "compared to last year" / "year-over-year" → Use metric vs metric_ly
- "considering last spring, plan for this spring" → Use metric vs metric_ly (YoY planning)
- "weather-driven risks" → Use metric vs metric_ly (negative values = risk)

SEASONS: Spring=Feb/Mar/Apr, Summer=May/Jun/Jul, Fall=Aug/Sep/Oct, Winter=Nov/Dec/Jan
""")
        
        # SQL generation instructions
        prompt_parts.append("""
IMPORTANT SQL GENERATION RULES:
1. Use PostgreSQL syntax (LIMIT not TOP, || for concat)
2. FIRST determine query type (see QUERY TYPE DETECTION above)

=== QUERY TYPE EXAMPLES (Study These!) ===

**TYPE 1 - SALES ONLY** (Use sales table):
Q: "How did the sales of Cleaning Supplies change in Chicago during cold spells in February 2024?"
→ Use: sales table + weekly_weather (join on cold_spell_flag = true)
→ CRITICAL: User said "Cleaning Supplies" (specific product), so filter by product name:
→ WHERE ph.product = 'Cleaning Supplies' (NOT by category!)
→ SELECT ph.product, SUM(s.sales_units), SUM(s.sales_units * s.total_amount) as revenue FROM sales s...

Q: "How did Smoothies perform in Charlotte, NC during heatwave weeks in 2025?"
→ Use: sales table + weekly_weather (join on heatwave_flag = true)
→ CRITICAL: User said "Smoothies" (specific product)
→ Filter: WHERE ph.product = 'Smoothies' (NOT WHERE ph.category = 'QSR'!)
→ Focus on actual units sold and revenue for SMOOTHIES ONLY

Q: "Which region had the fastest growing demand for salad kits between 2023 and 2025?"
→ Use: sales table with calendar.year for NRF fiscal year grouping
→ CRITICAL: Use calendar.year IN (2023, 2024, 2025) - NRF calendar handles the date ranges!
→ Do NOT add extra BETWEEN date filters when using calendar.year!
→ Calculate growth from 2023 to 2025 using CASE WHEN or FILTER clause
→ Example SQL:
   SELECT l.region,
          SUM(CASE WHEN c.year = 2025 THEN s.sales_units ELSE 0 END) AS units_2025,
          SUM(CASE WHEN c.year = 2023 THEN s.sales_units ELSE 0 END) AS units_2023,
          ROUND((SUM(CASE WHEN c.year = 2025 THEN s.sales_units ELSE 0 END) - 
                 SUM(CASE WHEN c.year = 2023 THEN s.sales_units ELSE 0 END)) /
                NULLIF(SUM(CASE WHEN c.year = 2023 THEN s.sales_units ELSE 0 END), 0) * 100, 2) AS growth_pct
   FROM sales s
   JOIN product_hierarchy ph ON s.product_code = ph.product_id
   JOIN location l ON s.store_code = l.location
   JOIN calendar c ON s.transaction_date = c.end_date
   WHERE ph.product = 'Salad Kits'
     AND c.year IN (2023, 2025)  -- Only the years needed for comparison
   GROUP BY l.region
   HAVING SUM(CASE WHEN c.year = 2023 THEN s.sales_units ELSE 0 END) > 0  -- Ensure 2023 baseline exists
   ORDER BY growth_pct DESC;

**TYPE 2 - WDD + SALES COMBINED** (Join metrics AND sales):
Q: "Sandwich sales were down in Southeast last month. How much was due to weather?"
→ Use: metrics (for WDD trend) + sales (for actual sales performance)
→ Compare WDD change (metric vs metric_ly) against actual sales change
→ Example SQL:
   SELECT 
       ph.product,
       SUM(s.sales_units) as actual_units,
       SUM(s.sales_units) - SUM(s_ly.sales_units) as sales_change,
       ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) as wdd_change_pct
   FROM sales s
   JOIN metrics m ON m.product = ph.product AND m.location = s.store_code AND m.end_date = ...
   JOIN sales s_ly ON ... (last year data)
   WHERE...

Q: "How much did weather affect demand in Apparel sector this past summer compared to prior summer?"
→ Use: metrics (WDD trends) + sales (actual sales)
→ Show both weather impact % AND actual sales difference
→ Example SQL:
   SELECT 
       ph.category,
       SUM(s.sales_units) as summer_2025_units,
       SUM(s_ly.sales_units) as summer_2024_units,
       ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) as wdd_impact_pct
   FROM sales s
   JOIN metrics m ON m.product = ph.product AND m.location = s.store_code AND m.end_date = s.transaction_date
   JOIN product_hierarchy ph ON s.product_code = ph.product_id
   WHERE ph.category = 'Apparel' AND c.month IN ('May', 'June', 'July')

Q: "Which markets had the most favorable weather impacts on restaurant traffic this Fall compared to last Fall?"
→ Use: metrics (WDD) + sales (actual traffic = sales_units)
→ Join both tables to show weather correlation with actual sales
→ Example SQL:
   SELECT 
       l.market,
       SUM(s.sales_units) as actual_traffic,
       ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) as wdd_impact_pct
   FROM sales s
   JOIN metrics m ON m.product = ph.product AND m.location = s.store_code
   JOIN location l ON s.store_code = l.store_id
   WHERE c.season = 'Fall' AND c.year = 2025

Q: "Based on the weather, what grocery products had the best year-over-year performance last quarter?"
→ Use: metrics (WDD trends) + sales (actual performance)
→ Filter by positive WDD impact, rank by sales YoY growth
→ Example SQL:
   SELECT 
       ph.product,
       SUM(s.sales_units) as current_qtr_units,
       SUM(s_ly.sales_units) as last_year_qtr_units,
       ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) as wdd_impact_pct
   FROM sales s
   JOIN metrics m ON m.product = ph.product AND m.location = s.store_code
   JOIN product_hierarchy ph ON s.product_code = ph.product_id
   WHERE ph.dept = 'Grocery' AND wdd_impact_pct > 0
   ORDER BY (current_qtr_units - last_year_qtr_units) DESC

Q: "Considering the impact of weather last spring, how should we plan for allergy relief this coming spring?"
→ Use: metrics (WDD trends with metric_ly for year-over-year comparison)
→ This is a PLANNING query with historical reference - use metric vs metric_ly!
→ Filter by product, season='Spring', show YoY WDD change
→ Example SQL:
   SELECT 
       ph.product,
       l.region,
       c.month,
       SUM(m.metric) as current_forecast,
       SUM(m.metric_ly) as last_year_demand,
       ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) as yoy_change_pct,
       ROUND(SUM(m.metric_ly) * (1 + (SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0)), 0) as recommended_order
   FROM metrics m
   JOIN product_hierarchy ph ON m.product = ph.product
   JOIN location l ON m.location = l.location
   JOIN calendar c ON m.end_date = c.end_date
   WHERE ph.product = 'Allergy Relief'
     AND c.season = 'Spring'
     AND c.year = 2026
   GROUP BY ph.product, l.region, c.month
   ORDER BY l.region, c.month

**TYPE 3 - WDD ONLY** (Use metrics table only):
Q: "What is the weather-driven demand forecast for ice cream?"
→ Use: metrics table only (trend analysis)
→ No sales join needed

**TYPE 6 - EVENT-BASED** (Use events + sales):
Q: "Which Non-Perishable products sold the most during the Los Angeles Lakers VS Golden State Warriors game week?"
→ First: Find event in events table
→ Then: Join with sales for actual sales during that week
→ Focus on sales_units from sales table

=== TABLE USAGE RULES ===
3. For WEATHER DEMAND analysis → Use 'metrics' table
4. For ACTUAL SALES data → Use 'sales' table (NOT metrics!)
5. For WDD + SALES COMBINED → JOIN both metrics and sales tables
6. For INVENTORY/STOCK → Use 'batches' and 'batch_stock_tracking' tables
7. For SPOILAGE/WASTE → Use 'spoilage_report' table
8. For EVENT analysis → Use 'events' table, join with sales for performance
   🚨 CRITICAL: Search BOTH e.event AND e.event_type columns!
   Example: WHERE (e.event ILIKE '%festival%' OR e.event_type ILIKE '%festival%')

🚨 CRITICAL - PRODUCT vs CATEGORY FILTERING:
- When user mentions SPECIFIC PRODUCT NAMES (e.g., "Sandwiches", "Smoothies", "Salad Kits"):
  ✅ CORRECT: WHERE ph.product = 'Sandwiches' OR WHERE ph.product IN ('Sandwiches', 'Tomatoes', 'Lettuce')
  ❌ WRONG: WHERE ph.category = 'QSR' (this returns ALL QSR products, not just Sandwiches!)
  
- 🚨🚨 ONLY filter by the EXACT products the user mentioned - DO NOT add ANY other products:
  User says: "Sandwiches, tomatoes, lettuce" (3 products)
  ✅ CORRECT: WHERE ph.product IN ('Sandwiches', 'Tomatoes', 'Lettuce')  -- Exactly 3 products
  ❌ WRONG: WHERE ph.product IN ('Sandwiches', 'Tomatoes', 'Lettuce', 'Salads', 'Salad Kits')  -- 5 products!
  ❌ WRONG: WHERE ph.category IN ('QSR', 'Perishable')  -- Would return 16 products!
  
- The number of products in your WHERE clause MUST match the number of products user mentioned!
  User mentions 3 products → WHERE clause must have EXACTLY 3 products
  User mentions 1 product → WHERE clause must have EXACTLY 1 product
  
- Only filter by category when user asks about the CATEGORY itself:
  ✅ CORRECT: "Show me all QSR products" → WHERE ph.category = 'QSR'
  ✅ CORRECT: "Perishable products" → WHERE ph.category = 'Perishable'
  
- For related products mentioned explicitly by user:
  ✅ CORRECT: "demand for tomatoes, lettuce" → WHERE ph.product IN ('Tomatoes', 'Lettuce')
  ❌ WRONG: WHERE ph.category = 'Perishable' (returns 8 products instead of 2!)

CRITICAL - REVENUE CALCULATION:
- Total Sale Units = SUM(sales_units)
- Revenues = SUM(sales_units * total_amount)  ← ALWAYS USE THIS FORMULA!
- NEVER use SUM(total_amount) alone for revenue
- Example: SELECT product, SUM(sales_units) as units, SUM(sales_units * total_amount) as revenue FROM sales...

🚨 CRITICAL - WEATHER FLAG FILTERING:
- When user mentions "heatwave", "heat wave", or "hot weather" → MUST filter: WHERE heatwave_flag = true
- When user mentions "cold spell", "cold weather", "freezing" → MUST filter: WHERE cold_spell_flag = true  
- When user mentions "heavy rain", "rainy", "precipitation" → MUST filter: WHERE heavy_rain_flag = true
- When user mentions "snow", "snowy" → MUST filter: WHERE snow_flag = true
- Join weekly_weather: JOIN weekly_weather w ON w.week_end_date = c.end_date AND w.store_id = l.location
- CRITICAL: weekly_weather uses week_end_date NOT end_date!
- Example WRONG: JOIN weekly_weather w ON w.end_date = c.end_date ❌ (column doesn't exist!)
- Example CORRECT: JOIN weekly_weather w ON w.week_end_date = c.end_date ✅
- Example CORRECT: "heatwave impact" → WHERE w.heatwave_flag = true ✅

🚨 CRITICAL - COMPARISON QUERIES ("vs" or "compared to"):
- When user asks "heatwave vs normal", "cold spell vs normal", "event weeks vs non-event" → Use CASE statements!
- Calculate BOTH conditions separately in same query:
  SUM(CASE WHEN w.heatwave_flag = true THEN s.sales_units ELSE 0 END) AS heatwave_sales,
  SUM(CASE WHEN w.heatwave_flag = false THEN s.sales_units ELSE 0 END) AS normal_sales
- This allows direct comparison in one result set
- Example: "Smoothies during heatwave vs normal weeks" → Use CASE to split by heatwave_flag
- REMEMBER: JOIN weekly_weather w ON w.week_end_date = c.end_date (NOT w.end_date!)

CRITICAL - ENTITY VALIDATION:
- Valid regions ONLY: 'northeast', 'southeast', 'midwest', 'west', 'southwest' (all lowercase)
- If user mentions invalid region (e.g., "Midwest" with capital M, "pacific", "central"), query will return 0 rows
- Check events table for actual events - if event doesn't exist, SQL returns 0 rows (this is CORRECT)
- Never fabricate data - 0 rows means NO DATA EXISTS for that criteria

CRITICAL JOIN RULES:
- sales/batches/spoilage use product_code (INTEGER) → joins with product_hierarchy.product_id
- metrics uses product (STRING) → joins with product_hierarchy.product
- All inventory tables use store_code → joins with location.location

8. For REGION queries: l.region = 'northeast' (LOWERCASE!)
9. calendar.month is STRING ('January', 'December') NOT integer!
10. ALWAYS use NULLIF(denominator, 0) to prevent division by zero
11. Use SELECT DISTINCT unless aggregating with GROUP BY
12. Maximum 30 rows (use LIMIT 30)
13. Return ONLY the SQL query, no explanation

=== SPECIAL CASES ===

**"Ideal Beach Weather" / "Perfect Weather" Queries:**
Q: "How should food options be diversified for peak weekend sales driven by ideal beach weather in Miami?"
→ Strategy:
   1. Find weeks with "ideal beach weather" using weekly_weather table:
      - Temperature: tmax_f BETWEEN 75 AND 90 (warm but not extreme)
      - Low precipitation: precip_in < 0.3 (minimal rain - average is 0.59)
      - No extreme flags: heatwave_flag = false, heavy_rain_flag = false
   2. Join with sales table to see what sold best during those ideal weeks
   3. Filter by Miami market (location.market ILIKE '%miami%')
   4. Group by product category to see diversification opportunities
   5. Include week-over-week comparison for trend analysis

Example SQL:
SELECT ph.category, ph.product, 
       SUM(s.sales_units) as total_units,
       SUM(s.sales_units * s.total_amount) as revenue
FROM sales s
JOIN product_hierarchy ph ON s.product_code = ph.product_id
JOIN location l ON s.store_code = l.location
JOIN calendar c ON s.transaction_date = c.end_date
JOIN weekly_weather w ON w.week_end_date = c.end_date AND w.store_id = l.location
WHERE l.market ILIKE '%miami%'
  AND w.tmax_f BETWEEN 75 AND 90
  AND w.precip_in < 0.3  -- Low precipitation = ideal beach weather
  AND w.heatwave_flag = false
  AND w.heavy_rain_flag = false
GROUP BY ph.category, ph.product
ORDER BY total_units DESC
LIMIT 20;

**"Cold Spell / Heatwave Impact + Ordering Recommendations" Queries:**
Q: "Our store is in Northeast expecting a cold spell. What is the decrease in demand for Salad Kits and how to adjust ordering?"
→ Strategy:
   1. Use metrics table to get WDD trend during cold spells (to show weather impact)
   2. Filter by SPECIFIC product mentioned (Salad Kits) - NOT all products!
   3. Filter by region (northeast)
   4. Calculate demand change using metric vs metric_nrm (short-term) - this shows the PERCENTAGE change
   5. For ordering recommendations: Use the WDD % to adjust ACTUAL last-week sales

Example SQL (WDD percentage analysis):
SELECT ph.product, l.region,
       ROUND((SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) * 100, 2) AS demand_change_pct,
       SUM(m.metric) as forecasted_trend,
       SUM(m.metric_nrm) as normal_trend
FROM metrics m
JOIN product_hierarchy ph ON m.product = ph.product
JOIN location l ON m.location = l.location
JOIN calendar c ON m.end_date = c.end_date
JOIN weekly_weather w ON w.week_end_date = c.end_date AND w.store_id = l.location
WHERE ph.product = 'Salad Kits'  -- CRITICAL: Filter by EXACT product mentioned!
  AND l.region = 'northeast'
  AND w.cold_spell_flag = true
GROUP BY ph.product, l.region
LIMIT 30;

-- NOTE: For recommended ordering quantity, use the Adjusted Qty formula:
-- Recommended Qty = Last-week ACTUAL sales × (1 + WDD %)
-- Get last-week sales from sales table, NOT from metrics!

**"Rise in Sales Without Weather/Event" Queries (Anomaly Detection):**
Q: "Alert me to products in Columbia, SC that experienced a rise in sales but no weather or event recorded"
→ Strategy:
   1. Compare current period sales to previous period (week-over-week)
   2. LEFT JOIN to weekly_weather and filter for NORMAL conditions (flags = false, NOT NULL!)
   3. LEFT JOIN to events and check for NULL (no events)
   4. Calculate sales growth percentage
   
⚠️ CRITICAL - Weather Flag Logic:
   - heatwave_flag = false → Normal weather (NO heatwave) ✓ CORRECT
   - heatwave_flag IS NULL → No weather data exists ✗ WRONG
   - Same applies to: heavy_rain_flag, cold_spell_flag, snow_flag
   
Example SQL:
WITH current_sales AS (
    SELECT ph.product, SUM(s.sales_units) AS current_units
    FROM sales s
    JOIN product_hierarchy ph ON s.product_code = ph.product_id
    JOIN location l ON s.store_code = l.location
    LEFT JOIN weekly_weather w ON w.week_end_date = s.transaction_date AND w.store_id = l.location
    LEFT JOIN events e ON e.event_date = s.transaction_date AND e.store_id = l.location
    WHERE l.market ILIKE '%columbia, sc%'
      AND s.transaction_date BETWEEN '2025-10-01' AND '2025-11-08'
      AND (w.heatwave_flag = false OR w.heatwave_flag IS NULL)  -- No heatwave OR no weather data
      AND (w.heavy_rain_flag = false OR w.heavy_rain_flag IS NULL)  -- No heavy rain OR no weather data
      AND (w.cold_spell_flag = false OR w.cold_spell_flag IS NULL)  -- No cold spell OR no weather data
      AND e.event IS NULL  -- No events recorded
    GROUP BY ph.product
),
previous_sales AS (
    SELECT ph.product, SUM(s.sales_units) AS previous_units
    FROM sales s
    JOIN product_hierarchy ph ON s.product_code = ph.product_id
    JOIN location l ON s.store_code = l.location
    WHERE l.market ILIKE '%columbia, sc%'
      AND s.transaction_date BETWEEN '2025-09-01' AND '2025-09-30'
    GROUP BY ph.product
)
SELECT cs.product,
       cs.current_units,
       ps.previous_units,
       ROUND((cs.current_units - ps.previous_units)::NUMERIC / NULLIF(ps.previous_units, 0) * 100, 2) AS growth_pct
FROM current_sales cs
JOIN previous_sales ps ON cs.product = ps.product
WHERE cs.current_units > ps.previous_units
ORDER BY growth_pct DESC
LIMIT 30;

**"Heatwave Impact on Perishables + Shrinkage Risk" Queries:**
Q: "Sudden heatwave in San Francisco. How could this impact perishable products and shrinkage risk?"
→ Strategy:
   1. Get WDD forecast for perishable products during heatwave
   2. Also get historical sales during past heatwaves for trend analysis
   3. Filter by category = 'Perishable' for all perishable products
   4. Join with spoilage_report for shrinkage/waste data during hot periods

Example SQL for WDD + Historical Analysis (NO future date filter - use historical heatwave data):
SELECT ph.product,
       ROUND((SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) * 100, 2) AS wdd_change_pct,
       SUM(m.metric) as forecasted_demand,
       SUM(m.metric_nrm) as normal_demand
FROM metrics m
JOIN product_hierarchy ph ON m.product = ph.product
JOIN location l ON m.location = l.location
JOIN calendar c ON m.end_date = c.end_date
JOIN weekly_weather w ON w.week_end_date = c.end_date AND w.store_id = l.location
WHERE ph.category = 'Perishable'  -- All perishable products
  AND l.market ILIKE '%san francisco%'
  AND w.heatwave_flag = true
  -- NO future date filter! Use all historical heatwave data to predict impact
GROUP BY ph.product
ORDER BY wdd_change_pct DESC
LIMIT 30;

**"Recommended Ordering Volume" Queries (CRITICAL - MUST USE ACTUAL SALES!):**
===================================================================================
Q: "What is the recommended ordering volume for perishables in Tampa considering weather forecast?"
Q: "What should we order for next week considering weather?"
Q: "Recommend ordering quantity for perishables"

⚠️ CRITICAL FORMULA (from Testing Team) - DO NOT USE metric_nrm OR metric_ly AS BASELINE!
===================================================================================
Adjusted Qty = Last-week ACTUAL sales × (1 + WDD %)

This formula MUST use:
1. ACTUAL sales from SALES TABLE (last week) as the baseline - NOT metric_nrm or metric_ly!
2. WDD percentage from metrics table (for next week) as the multiplier
3. NEVER use metric_nrm or metric_ly as the baseline - they are TREND values, not real sales!

WRONG (DO NOT DO THIS - Q5 ERROR):
❌ metric_nrm * (1 + wdd_pct) AS recommended_order  -- WRONG! metric_nrm is NOT real sales
❌ SUM(m.metric_ly) * (1 + ...) AS recommended_order  -- WRONG! metric_ly is last YEAR metrics, NOT last week sales
❌ SUM(m.metric_nrm) * (1 + ...) AS recommended_order  -- WRONG!

CORRECT (ALWAYS DO THIS FOR Q5):
✅ last_week_sales.units * (1 + wdd_pct) AS recommended_order  -- Uses REAL sales from sales table!
✅ FROM sales s WHERE s.transaction_date BETWEEN '2025-11-02' AND '2025-11-08'  -- Last week ACTUAL sales

→ Strategy:
   1. Get ACTUAL SALES from sales table for last week (transaction_date BETWEEN '2025-11-02' AND '2025-11-08')
   2. Get WDD % from metrics table for next week (metric vs metric_nrm)
   3. Calculate: recommended_order = last_week_sales × (1 + WDD_pct)

Example SQL (CORRECT approach - MUST use CTE pattern with sales table):
WITH last_week_sales AS (
    -- Get ACTUAL sales from sales table (NOT from metrics!)
    SELECT ph.product, SUM(s.sales_units) as last_week_units
    FROM sales s
    JOIN product_hierarchy ph ON s.product_code = ph.product_id
    JOIN location l ON s.store_code = l.location
    WHERE s.transaction_date BETWEEN '2025-11-02' AND '2025-11-08'  -- Last week
      AND l.market ILIKE '%tampa%'
      AND ph.category = 'Perishable'
    GROUP BY ph.product
),
wdd_forecast AS (
    -- Get WDD percentage from metrics table for next week
    SELECT m.product,
        (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) AS wdd_pct
    FROM metrics m
    JOIN location l ON m.location = l.location
    WHERE m.end_date = '2025-11-15'  -- Next week
      AND l.market ILIKE '%tampa%'
    GROUP BY m.product
)
SELECT 
    lws.product,
    lws.last_week_units AS last_week_sales,
    ROUND(COALESCE(w.wdd_pct, 0) * 100, 2) AS wdd_change_pct,
    ROUND(lws.last_week_units * (1 + COALESCE(w.wdd_pct, 0)), 0) AS recommended_order_qty
FROM last_week_sales lws
LEFT JOIN wdd_forecast w ON lws.product = w.product
ORDER BY wdd_change_pct DESC
LIMIT 30;

14. WHERE vs HAVING CLAUSE (CRITICAL - PREVENTS ERRORS!):
    - WHERE clause: Filters rows BEFORE grouping - NO aggregate functions (SUM, AVG, COUNT, etc.)
    - HAVING clause: Filters groups AFTER grouping - aggregate functions ARE ALLOWED
    
    WRONG Examples (will cause ERROR):
    ❌ WHERE SUM(metric) > 100
    ❌ WHERE AVG(sales_units) > 50
    ❌ WHERE ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) > 0
    
    CORRECT Examples:
    ✅ HAVING SUM(metric) > 100
    ✅ HAVING AVG(sales_units) > 50
    ✅ HAVING ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) > 0
    
    Rule: If filtering by aggregated/calculated values after GROUP BY, use HAVING not WHERE!

15. HANDLING MISSING CATEGORY/DEPARTMENT (CRITICAL!):
    When grouping by category or department, use COALESCE to fallback to product name:
    - SELECT COALESCE(ph.category, ph.product) AS category FROM ...
    - SELECT COALESCE(ph.dept, ph.product) AS department FROM ...
    - GROUP BY COALESCE(ph.category, ph.product)
    This prevents "None (Missing)" - shows product name when category/dept is NULL
    
    Example for category query:
    SELECT COALESCE(ph.category, ph.product) AS category,
           ROUND((SUM(m.metric) - SUM(m.metric_ly)) / NULLIF(SUM(m.metric_ly), 0) * 100, 2) AS wdd_change
    FROM metrics m
    JOIN product_hierarchy ph ON m.product = ph.product
    GROUP BY COALESCE(ph.category, ph.product)
    ORDER BY wdd_change DESC

CRITICAL TABLE NAMES:
- metrics (WDD trends)
- sales (actual transactions)
- batches (inventory batches)
- batch_stock_tracking (stock movements)
- spoilage_report (waste tracking)
- events (festivals, holidays, games)
- weekly_weather
- location
- product_hierarchy
- calendar
- perishable

=== EXAMPLE QUERY PATTERNS ===

-- WDD Analysis: "weather impact on demand"
SELECT ph.product, l.region, ROUND((SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) * 100, 2) AS wdd_vs_normal_pct
FROM metrics m
JOIN product_hierarchy ph ON m.product = ph.product
JOIN location l ON m.location = l.location
JOIN calendar c ON m.end_date = c.end_date
WHERE c.end_date BETWEEN '2025-11-08' AND '2025-11-22'
GROUP BY ph.product, l.region ORDER BY wdd_vs_normal_pct DESC LIMIT 30

-- SALES Query: "top selling products"  
SELECT ph.product, SUM(s.sales_units) AS total_units, SUM(s.total_amount) AS total_revenue
FROM sales s
JOIN product_hierarchy ph ON s.product_code = ph.product_id
WHERE s.transaction_date >= '2025-10-01'
GROUP BY ph.product ORDER BY total_revenue DESC LIMIT 30

-- INVENTORY Query: "products low on stock"
SELECT ph.product, l.location, SUM(b.stock_at_week_end) AS current_stock
FROM batches b
JOIN product_hierarchy ph ON b.product_code = ph.product_id
JOIN location l ON b.store_code = l.location
WHERE b.week_end_date = '2025-11-08'
GROUP BY ph.product, l.location HAVING SUM(b.stock_at_week_end) < 100 LIMIT 30

-- EVENTS Query: "football games this week"
SELECT DISTINCT e.event, e.event_type, e.event_date, e.market, e.state
FROM events e
WHERE (e.event ILIKE '%football%' OR e.event_type ILIKE '%sporting%')
  AND e.event_date BETWEEN '2025-11-02' AND '2025-11-08'
ORDER BY e.event_date LIMIT 30

-- SPOILAGE Query: "products with highest waste"
SELECT ph.product, SUM(sr.spoilage_qty) AS total_spoilage, AVG(sr.spoilage_pct) AS avg_spoilage_pct
FROM spoilage_report sr
JOIN product_hierarchy ph ON sr.product_code = ph.product_id
GROUP BY ph.product ORDER BY total_spoilage DESC LIMIT 30

=== CFO-LEVEL BUSINESS FORMULAS (CRITICAL FOR ADVANCED ANALYTICS) ===

These formulas support inventory optimization, stockout risk analysis, financial loss prediction, and sales velocity tracking.
Use these when user asks about: stockout risk, overstock analysis, inventory turnover, sales velocity, demand forecasting, financial loss prediction.

**1. Daily Sales Velocity** (baseline selling speed):
   Formula: Total Sales in Last 28 Days / 28
   Purpose: Establish baseline daily selling rate per product/region
   PostgreSQL Example:
   WITH sales_velocity AS (
     SELECT ph.product, l.region,
            SUM(s.sales_units) / 28.0 AS daily_velocity
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
     GROUP BY ph.product, l.region
   )
   SELECT * FROM sales_velocity ORDER BY daily_velocity DESC;

**2. Adjusted Velocity** (weather-adjusted selling speed):
   Formula: Daily_Sales_Velocity × (1 + WDD_Pct_vs_Normal)
   Purpose: Predict future selling speed considering weather impacts
   PostgreSQL Example:
   WITH sales_velocity AS (
     SELECT ph.product, l.region,
            SUM(s.sales_units) / 28.0 AS daily_velocity
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
     GROUP BY ph.product, l.region
   ),
   wdd_forecast AS (
     SELECT m.product, m.location,
            (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) AS wdd_pct
     FROM metrics m
     JOIN calendar c ON m.end_date = c.end_date
     WHERE c.end_date >= '2025-11-15'  -- next week
     GROUP BY m.product, m.location
   )
   SELECT sv.product, sv.region,
          sv.daily_velocity * (1 + COALESCE(w.wdd_pct, 0)) AS adjusted_velocity
   FROM sales_velocity sv
   LEFT JOIN wdd_forecast w ON sv.product = w.product AND sv.region = w.location;

**3. Adjusted Demand** (4-week average adjusted for weather):
   Formula: Avg_4Week_Sales × (1 + WDD_Pct_vs_Normal)
   Purpose: Forecast weekly demand considering weather impacts
   PostgreSQL Example:
   WITH avg_sales AS (
     SELECT ph.product, l.region,
            AVG(weekly_sales.units) AS avg_4week_sales
     FROM (
       SELECT s.product_code, s.store_code,
              DATE_TRUNC('week', s.transaction_date) AS week,
              SUM(s.sales_units) AS units
       FROM sales s
       WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
       GROUP BY s.product_code, s.store_code, week
     ) weekly_sales
     JOIN product_hierarchy ph ON weekly_sales.product_code = ph.product_id
     JOIN location l ON weekly_sales.store_code = l.location
     GROUP BY ph.product, l.region
   ),
   wdd_forecast AS (
     SELECT m.product, m.location,
            (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0) AS wdd_pct
     FROM metrics m
     GROUP BY m.product, m.location
   )
   SELECT a.product, a.region,
          a.avg_4week_sales * (1 + COALESCE(w.wdd_pct, 0)) AS adjusted_demand
   FROM avg_sales a
   LEFT JOIN wdd_forecast w ON a.product = w.product AND a.region = w.location;

**4. Stockout Loss** (potential revenue loss from stockouts):
   Formula: MAX(0, (Adjusted_Velocity × 7) - Current_Stock)
   Purpose: Identify products at risk of running out before next delivery
   PostgreSQL Example:
   WITH current_inventory AS (
     SELECT ph.product, l.region,
            SUM(b.stock_at_week_end) AS current_stock
     FROM batches b
     JOIN product_hierarchy ph ON b.product_code = ph.product_id
     JOIN location l ON b.store_code = l.location
     WHERE b.week_end_date = (SELECT MAX(week_end_date) FROM batches)
     GROUP BY ph.product, l.region
   ),
   velocity AS (
     SELECT ph.product, l.region,
            (SUM(s.sales_units) / 28.0) * (1 + COALESCE(
              (SELECT (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0)
               FROM metrics m WHERE m.product = ph.product AND m.location = l.location), 0
            )) AS adjusted_velocity
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
     GROUP BY ph.product, l.region
   )
   SELECT i.product, i.region, i.current_stock,
          v.adjusted_velocity * 7 AS weekly_demand,
          GREATEST(0, (v.adjusted_velocity * 7) - i.current_stock) AS stockout_loss_units
   FROM current_inventory i
   JOIN velocity v ON i.product = v.product AND i.region = v.region
   WHERE (v.adjusted_velocity * 7) > i.current_stock
   ORDER BY stockout_loss_units DESC;

**5. Week-on-Week Sales Unit % Change** (regional performance tracking):
   Formula: ((Current_Week_Sales - Previous_Week_Sales) / Previous_Week_Sales) × 100
   Purpose: Track sales momentum across regions
   PostgreSQL Example:
   WITH current_week AS (
     SELECT l.region, ph.product, SUM(s.sales_units) AS curr_units
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     WHERE s.transaction_date BETWEEN '2025-11-02' AND '2025-11-08'
     GROUP BY l.region, ph.product
   ),
   prev_week AS (
     SELECT l.region, ph.product, SUM(s.sales_units) AS prev_units
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     WHERE s.transaction_date BETWEEN '2025-10-26' AND '2025-11-01'
     GROUP BY l.region, ph.product
   )
   SELECT c.region, c.product,
          ROUND(((c.curr_units - p.prev_units)::NUMERIC / NULLIF(p.prev_units, 0)) * 100, 2) AS wow_change_pct
   FROM current_week c
   JOIN prev_week p ON c.region = p.region AND c.product = p.product
   ORDER BY wow_change_pct DESC;

**6. Sales Uplift vs Historical Average** (demand spike detection):
   Formula: Current_Week_Sales - Four_Week_Avg_Sales
   Purpose: Identify unusual demand spikes requiring inventory adjustment
   PostgreSQL Example:
   WITH current_week AS (
     SELECT ph.product, l.region, SUM(s.sales_units) AS current_units
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     WHERE s.transaction_date BETWEEN '2025-11-02' AND '2025-11-08'
     GROUP BY ph.product, l.region
   ),
   four_week_avg AS (
     SELECT ph.product, l.region, AVG(weekly.units) AS avg_units
     FROM (
       SELECT s.product_code, s.store_code,
              DATE_TRUNC('week', s.transaction_date) AS week,
              SUM(s.sales_units) AS units
       FROM sales s
       WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
       GROUP BY s.product_code, s.store_code, week
     ) weekly
     JOIN product_hierarchy ph ON weekly.product_code = ph.product_id
     JOIN location l ON weekly.store_code = l.location
     GROUP BY ph.product, l.region
   )
   SELECT c.product, c.region,
          c.current_units - a.avg_units AS sales_uplift
   FROM current_week c
   JOIN four_week_avg a ON c.product = a.product AND c.region = a.region
   WHERE c.current_units > a.avg_units
   ORDER BY sales_uplift DESC;

**7. Overstock Percentage by Region** (inventory efficiency):
   Formula: ((Current_Stock - Adjusted_Demand) / Adjusted_Demand) × 100
   Purpose: Identify regions with excess inventory requiring markdown/transfers
   PostgreSQL Example:
   WITH current_inventory AS (
     SELECT ph.product, l.region, SUM(b.stock_at_week_end) AS current_stock
     FROM batches b
     JOIN product_hierarchy ph ON b.product_code = ph.product_id
     JOIN location l ON b.store_code = l.location
     WHERE b.week_end_date = (SELECT MAX(week_end_date) FROM batches)
     GROUP BY ph.product, l.region
   ),
   demand_forecast AS (
     SELECT ph.product, l.region,
            AVG(weekly_sales.units) * (1 + COALESCE(
              (SELECT (SUM(m.metric) - SUM(m.metric_nrm)) / NULLIF(SUM(m.metric_nrm), 0)
               FROM metrics m WHERE m.product = ph.product AND m.location = l.location), 0
            )) AS adjusted_demand
     FROM (
       SELECT s.product_code, s.store_code, DATE_TRUNC('week', s.transaction_date) AS week,
              SUM(s.sales_units) AS units
       FROM sales s
       WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
       GROUP BY s.product_code, s.store_code, week
     ) weekly_sales
     JOIN product_hierarchy ph ON weekly_sales.product_code = ph.product_id
     JOIN location l ON weekly_sales.store_code = l.location
     GROUP BY ph.product, l.region
   )
   SELECT i.product, i.region,
          ROUND(((i.current_stock - d.adjusted_demand)::NUMERIC / NULLIF(d.adjusted_demand, 0)) * 100, 2) AS overstock_pct
   FROM current_inventory i
   JOIN demand_forecast d ON i.product = d.product AND i.region = d.region
   WHERE i.current_stock > d.adjusted_demand
   ORDER BY overstock_pct DESC;

**8. Shelf-Life Risk** (perishable loss prediction):
   Formulas:
   - Expiring Soon: SUM(stock WHERE days_to_expiry <= shelf_life_days) × Avg_Unit_Price
   - Already Expired: SUM(stock WHERE days_to_expiry < 0) × Avg_Unit_Price
   Purpose: Quantify financial risk from perishable spoilage
   PostgreSQL Example:
   WITH perishable_inventory AS (
     SELECT ph.product, l.region, b.batch_id,
            p.max_period AS shelf_life_days,
            b.stock_at_week_end,
            EXTRACT(DAY FROM (b.week_end_date - b.received_date)) AS days_since_received,
            p.max_period - EXTRACT(DAY FROM (b.week_end_date - b.received_date)) AS days_to_expiry
     FROM batches b
     JOIN product_hierarchy ph ON b.product_code = ph.product_id
     JOIN location l ON b.store_code = l.location
     JOIN perishable p ON ph.product = p.product
     WHERE b.week_end_date = (SELECT MAX(week_end_date) FROM batches)
       AND p.period_metric = 'Days'
   ),
   avg_prices AS (
     SELECT ph.product, AVG(s.total_amount) AS avg_unit_price
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     GROUP BY ph.product
   )
   SELECT pi.product, pi.region,
          SUM(CASE WHEN pi.days_to_expiry <= 7 AND pi.days_to_expiry > 0
                   THEN pi.stock_at_week_end * ap.avg_unit_price ELSE 0 END) AS expiring_soon_value,
          SUM(CASE WHEN pi.days_to_expiry <= 0
                   THEN pi.stock_at_week_end * ap.avg_unit_price ELSE 0 END) AS expired_value
   FROM perishable_inventory pi
   JOIN avg_prices ap ON pi.product = ap.product
   GROUP BY pi.product, pi.region
   HAVING SUM(CASE WHEN pi.days_to_expiry <= 7 THEN pi.stock_at_week_end ELSE 0 END) > 0
   ORDER BY expiring_soon_value + expired_value DESC;

**9. Stockout Rate** (SKU availability tracking):
   Formula: (SKUs_with_zero_stock / Total_SKUs) × 100
   Purpose: Measure inventory availability across product portfolio
   PostgreSQL Example:
   WITH inventory_status AS (
     SELECT ph.product, l.region,
            SUM(b.stock_at_week_end) AS current_stock
     FROM batches b
     JOIN product_hierarchy ph ON b.product_code = ph.product_id
     JOIN location l ON b.store_code = l.location
     WHERE b.week_end_date = (SELECT MAX(week_end_date) FROM batches)
     GROUP BY ph.product, l.region
   )
   SELECT region,
          COUNT(*) AS total_skus,
          SUM(CASE WHEN current_stock = 0 THEN 1 ELSE 0 END) AS stockout_skus,
          ROUND((SUM(CASE WHEN current_stock = 0 THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)) * 100, 2) AS stockout_rate_pct
   FROM inventory_status
   GROUP BY region
   ORDER BY stockout_rate_pct DESC;

**10. Predicted Total Loss** (comprehensive risk assessment):
   Formula: Shelf_Life_Loss + Overstock_Loss
   Purpose: Estimate total financial risk from inventory issues
   PostgreSQL Example:
   -- Combine shelf-life risk (Formula #8) with overstock risk (Formula #7)
   WITH shelf_life_risk AS (
     -- Use Formula #8 logic here
     SELECT product, region, SUM(expiring_value + expired_value) AS shelf_life_loss
     FROM (/* shelf-life calculation */) sub
     GROUP BY product, region
   ),
   overstock_risk AS (
     -- Use Formula #7 logic with markdown assumption (20% loss on excess)
     SELECT product, region,
            GREATEST(0, current_stock - adjusted_demand) * avg_unit_price * 0.2 AS overstock_loss
     FROM (/* overstock calculation */) sub
   )
   SELECT COALESCE(s.product, o.product) AS product,
          COALESCE(s.region, o.region) AS region,
          COALESCE(s.shelf_life_loss, 0) + COALESCE(o.overstock_loss, 0) AS predicted_total_loss
   FROM shelf_life_risk s
   FULL OUTER JOIN overstock_risk o ON s.product = o.product AND s.region = o.region
   ORDER BY predicted_total_loss DESC;

=== NEW CRITICAL FORMULAS (Testing Requirements) ===

**11. Weeks of Cover (WOC)** - Inventory Risk Assessment:
   Formula: Current_Stock / Average_Weekly_Sales
   Purpose: Measure how many weeks current inventory will last
   Risk Levels:
   - HIGH RISK: < 1 week of cover
   - MEDIUM RISK: 1 to < 2 weeks of cover
   - LOW RISK: ≥ 2 weeks of cover
   
   PostgreSQL Example:
   WITH weekly_sales AS (
     SELECT ph.product, l.location,
            AVG(week_sales.units) AS avg_weekly_sales
     FROM (
       SELECT s.product_code, s.store_code,
              DATE_TRUNC('week', s.transaction_date) AS week,
              SUM(s.sales_units) AS units
       FROM sales s
       WHERE s.transaction_date BETWEEN '2025-10-12' AND '2025-11-08'  -- Last 4 weeks
       GROUP BY s.product_code, s.store_code, week
     ) week_sales
     JOIN product_hierarchy ph ON week_sales.product_code = ph.product_id
     JOIN location l ON week_sales.store_code = l.location
     GROUP BY ph.product, l.location
   ),
   current_inventory AS (
     SELECT ph.product, l.location,
            SUM(b.stock_at_week_end) AS current_stock
     FROM batches b
     JOIN product_hierarchy ph ON b.product_code = ph.product_id
     JOIN location l ON b.store_code = l.location
     WHERE b.week_end_date = '2025-12-27'  -- Current week end
     GROUP BY ph.product, l.location
   )
   SELECT ci.product, ci.location,
          ci.current_stock,
          ws.avg_weekly_sales,
          ROUND(ci.current_stock / NULLIF(ws.avg_weekly_sales, 0), 2) AS weeks_of_cover,
          CASE 
            WHEN ci.current_stock / NULLIF(ws.avg_weekly_sales, 0) < 1 THEN 'HIGH RISK'
            WHEN ci.current_stock / NULLIF(ws.avg_weekly_sales, 0) < 2 THEN 'MEDIUM RISK'
            ELSE 'LOW RISK'
          END AS risk_level,
          CASE 
            WHEN ci.current_stock / NULLIF(ws.avg_weekly_sales, 0) < 1 THEN 1
            WHEN ci.current_stock / NULLIF(ws.avg_weekly_sales, 0) < 2 THEN 2
            ELSE 3
          END AS risk_priority
   FROM current_inventory ci
   JOIN weekly_sales ws ON ci.product = ws.product AND ci.location = ws.location
   WHERE ci.current_stock > 0
   ORDER BY weeks_of_cover ASC;

**12. Weekend Filtering for Ideal Beach Weather**:
   Purpose: Filter for Saturday week_end_date with ideal beach conditions
   Conditions:
   - Temperature: 80-95°F (use tmax, tmin from weekly_weather)
   - Rain: ≤ 0.1 inches (use percin column)
   - No adverse weather flags: heavy_rain = false, cold_spell = false, snow = false
   - Day of week: Saturday (week_end_date)
   
   PostgreSQL Example:
   SELECT DISTINCT c.end_date
   FROM calendar c
   JOIN weekly_weather ww ON c.end_date = ww.week_end_date
   WHERE EXTRACT(DOW FROM c.end_date) = 6  -- Saturday = 6
     AND ww.tmax BETWEEN 80 AND 95
     AND ww.tmin >= 70  -- Comfortable minimum
     AND ww.percin <= 0.1
     AND ww.heavy_rain = false
     AND ww.cold_spell = false
     AND ww.snow = false
     AND c.end_date BETWEEN '2023-11-08' AND '2025-11-08'  -- Last 2 years
   ORDER BY c.end_date;

**13. Quarter-on-Quarter (QoQ) Sales Comparison**:
   Purpose: Compare sales performance across quarters to identify spikes
   Formula: ((Current_Quarter_Sales - Previous_Quarter_Sales) / Previous_Quarter_Sales) × 100
   
   PostgreSQL Example:
   WITH quarterly_sales AS (
     SELECT ph.product, l.market,
            c.quarter, c.year,
            SUM(s.sales_units) AS total_units
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     JOIN calendar c ON DATE_TRUNC('week', s.transaction_date)::date = c.end_date
     WHERE c.end_date BETWEEN '2023-07-01' AND '2025-11-08'  -- Last 8 quarters
     GROUP BY ph.product, l.market, c.quarter, c.year
   ),
   lagged_sales AS (
     SELECT *,
            LAG(total_units) OVER (PARTITION BY product, market ORDER BY year, quarter) AS prev_quarter_units
     FROM quarterly_sales
   )
   SELECT product, market, quarter, year, total_units, prev_quarter_units,
          ROUND(((total_units - prev_quarter_units)::NUMERIC / NULLIF(prev_quarter_units, 0)) * 100, 2) AS qoq_change_pct
   FROM lagged_sales
   WHERE prev_quarter_units IS NOT NULL
   ORDER BY qoq_change_pct DESC;

**14. Event Proximity Checking**:
   Purpose: Check if events occurred near stores during specific weeks
   Logic: Find events within same market/state during the week
   
   PostgreSQL Example:
   SELECT DISTINCT c.end_date, l.market, l.state,
          COUNT(e.event) AS event_count,
          STRING_AGG(e.event, ', ') AS events_nearby
   FROM calendar c
   CROSS JOIN location l
   LEFT JOIN events e ON l.market = e.market 
     AND e.event_date BETWEEN c.end_date - INTERVAL '7 days' AND c.end_date
   WHERE c.end_date IN ('2025-01-11', '2025-01-18', '2025-02-15')  -- Specific weeks
     AND l.market = 'columbia, sc'
   GROUP BY c.end_date, l.market, l.state
   HAVING COUNT(e.event) = 0;  -- Only weeks with NO events

**15. Improved Shelf Life Risk with Daily Sales Velocity**:
   Purpose: Calculate precise expiry risk using daily selling rate
   Formula:
   - Days to Expiry > 0: Shelf_Life_Loss = (Current_Stock - (Daily_Sales_Velocity × Days_To_Expiry)) × Unit_Price
   - Days to Expiry ≤ 0: Shelf_Life_Loss = Current_Stock × Unit_Price
   
   PostgreSQL Example:
   WITH daily_velocity AS (
     SELECT ph.product, l.location,
            SUM(s.sales_units) / 28.0 AS daily_sales_velocity
     FROM sales s
     JOIN product_hierarchy ph ON s.product_code = ph.product_id
     JOIN location l ON s.store_code = l.location
     WHERE s.transaction_date >= CURRENT_DATE - INTERVAL '28 days'
     GROUP BY ph.product, l.location
   ),
   perishable_stock AS (
     SELECT ph.product, l.location, b.batch_id,
            b.stock_at_week_end AS current_stock,
            p.max_period - EXTRACT(DAY FROM ('2025-11-08'::date - b.received_date)) AS days_to_expiry,
            (SELECT AVG(total_amount) FROM sales WHERE product_code = b.product_code) AS unit_price
     FROM batches b
     JOIN product_hierarchy ph ON b.product_code = ph.product_id
     JOIN location l ON b.store_code = l.location
     JOIN perishable p ON ph.product = p.product
     WHERE b.week_end_date = '2025-11-08'
   )
   SELECT ps.product, ps.location,
          ps.current_stock,
          dv.daily_sales_velocity,
          ps.days_to_expiry,
          CASE 
            WHEN ps.days_to_expiry > 0 THEN 
              GREATEST(0, ps.current_stock - (dv.daily_sales_velocity * ps.days_to_expiry)) * ps.unit_price
            ELSE 
              ps.current_stock * ps.unit_price
          END AS shelf_life_loss
   FROM perishable_stock ps
   JOIN daily_velocity dv ON ps.product = dv.product AND ps.location = dv.location
   WHERE ps.days_to_expiry <= 7
   ORDER BY shelf_life_loss DESC;

=== WHEN TO USE CFO FORMULAS ===
- "stockout risk" / "running out" → Use Formula #4 (Stockout Loss)
- "inventory optimization" / "overstock" → Use Formula #7 (Overstock %)
- "sales velocity" / "selling speed" → Use Formula #1 (Daily Sales Velocity) or #2 (Adjusted Velocity)
- "demand forecast" / "order planning" → Use Formula #3 (Adjusted Demand)
- "week-over-week" / "regional performance" → Use Formula #5 (WoW Change)
- "demand spike" / "unusual sales" → Use Formula #6 (Sales Uplift)
- "perishable risk" / "expiring stock" → Use Formula #8 or #15 (Shelf-Life Risk)
- "SKU availability" / "out of stock rate" → Use Formula #9 (Stockout Rate)
- "financial loss" / "total risk" → Use Formula #10 (Predicted Total Loss)
- "weeks of cover" / "inventory duration" / "how long will stock last" → Use Formula #11 (Weeks of Cover)
- "weekend sales" / "beach weather" → Use Formula #12 (Weekend Filtering)
- "quarter comparison" / "quarterly growth" → Use Formula #13 (QoQ Comparison)
- "event proximity" / "no events nearby" → Use Formula #14 (Event Proximity)
- "prevent waste" / "ordering advice" / "adjust ordering" → MUST USE BOTH:
  1. Formula #3 (Adjusted Demand) for recommended order quantity
  2. Formula #15 (Shelf Life Risk) for waste prevention analysis
  3. Include daily_sales_velocity, current_stock, days_to_expiry, potential_waste_units

CRITICAL FOR Q3-TYPE QUERIES (prevent waste + adjust ordering):
When query asks about "prevent waste", "adjust ordering", or "ordering advice" for perishables:
- ALWAYS include shelf life risk calculation (Formula #15)
- ALWAYS calculate daily sales velocity
- ALWAYS check current stock levels from batches
- ALWAYS calculate days to expiry
- ALWAYS provide potential waste units
- Answer MUST address BOTH: (1) demand change % AND (2) specific waste prevention advice

Generate the PostgreSQL SELECT query:
""")
        
        return "\n".join(prompt_parts)
    
    def format_context_summary(self, context: Dict[str, Any]) -> str:
        """Format context as human-readable summary for debugging/logging"""
        summary = []
        
        products = context.get("products", {})
        if products.get("resolved"):
            summary.append(f"✓ {len(products['resolved'])} products identified")
        if products.get("expanded"):
            summary.append(f"✓ Expanded to {len(products['expanded'])} related products")
        
        locations = context.get("locations", {})
        if locations.get("resolved"):
            summary.append(f"✓ {len(locations['resolved'])} locations identified")
        if locations.get("expanded"):
            summary.append(f"✓ Expanded to {len(locations['expanded'])} stores")
        
        dates = context.get("dates", {})
        if dates.get("date_range"):
            summary.append(f"✓ Date range: {dates['date_range'][0]} to {dates['date_range'][1]}")
        
        events = context.get("events", {})
        if events.get("resolved"):
            summary.append(f"✓ {len(events['resolved'])} events found")
        
        return " | ".join(summary) if summary else "No specific context resolved"


# Global instance
context_resolver = ContextResolver()
