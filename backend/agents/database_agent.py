from typing import Dict, Any, List
from decimal import Decimal
from openai import AzureOpenAI
from sqlalchemy import text
from core.config import settings
from core.logger import logger
from database.postgres_db import get_db
from services.context_resolver import context_resolver


class DatabaseAgent:
    """
    THE ONLY AGENT THAT EXECUTES SQL QUERIES
    
    This agent is the single point of SQL execution in the clean architecture.
    All other agents are "domain experts" that provide hints about their domain.
    
    Workflow:
    1. Receive query + resolved context + domain hints from experts
    2. Build comprehensive prompt with all hints
    3. Generate optimized SQL with LLM
    4. Execute query on PostgreSQL
    5. Return results for synthesis
    
    Domain Expert Agents provide:
    - Table schemas relevant to their domain
    - Key column explanations
    - Join patterns
    - Business formulas (WDD, CFO calculations)
    - Time context and filters
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.OPENAI_ENDPOINT
        )
        self.resolver = context_resolver
        
        # Current date context (STATIC for demo data - Nov 8, 2025)
        self.CURRENT_WEEKEND_DATE = "2025-11-08"  # This weekend's end_date
        
        # MINIMAL system prompt - detailed schema is provided by context_resolver and domain hints
        self.system_prompt = """You are a PostgreSQL SQL expert for RETAIL SUPPLY CHAIN analytics.

=== YOUR ROLE ===
Generate accurate PostgreSQL SELECT queries based on:
1. User's natural language query  
2. Resolved entity context (products, locations, dates, events)
3. Database schema provided in the user prompt
4. Domain expert hints (formulas, join patterns, key columns)

=== CURRENT DATE CONTEXT ===
This Weekend: November 8, 2025 (2025-11-08)
- "this week" = end_date '2025-11-08'
- "next week" = end_date '2025-11-15'  
- "last week" = end_date '2025-11-01'
- "next month" = December 2025
- "last month" = October 2025

=== CRITICAL TABLE UNDERSTANDING ===
METRICS TABLE: Contains WDD TREND VALUES (NOT actual sales numbers!)
- Use to calculate WDD PERCENTAGE, then apply to actual sales
- metric = Weather-adjusted demand TREND
- metric_nrm = Normal demand TREND (use for FUTURE ≤4 weeks)
- metric_ly = Last Year demand TREND (use for PAST/YoY/>4 weeks)

SALES TABLE: Contains ACTUAL transaction data
- Use for actual revenue, units sold, real sales performance
- sales_units, total_amount = real transaction values

RECOMMENDED ORDER FORMULA: Last-week sales × (1 + WDD %)
- Get last_week_sales from SALES table (real units sold)
- Get WDD % from METRICS table (trend percentage)
- Multiply: recommended_qty = last_week_sales × (1 + wdd_pct)

=== CRITICAL RULES ===
1. PostgreSQL syntax: LIMIT (not TOP), || for concatenation
2. ALWAYS use NULLIF(denominator, 0) to prevent division errors
3. Region values are LOWERCASE: 'northeast', 'southeast', etc.
4. calendar.month is STRING ('January', 'February'), NOT integer
5. Revenue = SUM(sales_units * total_amount)
6. When user mentions SPECIFIC products, filter by exact product names
7. When user mentions CATEGORY, filter by category
8. Maximum 30 rows (use LIMIT 30)
9. Return ONLY the SQL query, no explanations

=== WDD FORMULA SELECTION ===
- FUTURE queries (≤4 weeks, next week, forecast): metric vs metric_nrm
- PAST queries (>4 weeks, last week, historical, YoY): metric vs metric_ly

The detailed schema, examples, and domain hints are provided in the user prompt below."""

        logger.info("🗄️ DatabaseAgent initialized (ONLY SQL executor)")

    def query_with_hints(
        self, 
        query: str, 
        context: Dict[str, Any] = None,
        domain_hints: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate and execute SQL using domain expert hints.
        
        This is the main entry point for the clean architecture pattern.
        
        Args:
            query: User's natural language query
            context: Resolved context from Azure Search + Gremlin
            domain_hints: List of hint dicts from domain expert agents
            
        Returns:
            Dict with sql_query, data, row_count, analysis, status
        """
        print("\n" + "="*80)
        print("🗄️ DATABASE AGENT - SQL Generation & Execution (Clean Architecture)")
        print("="*80)
        
        try:
            # Step 1: Resolve entities if not provided
            if context is None or not context.get("resolved"):
                print("\n📍 Step 1: Resolving context (Azure Search + Gremlin)...")
                resolved_context = self.resolver.resolve_query_context(query)
            else:
                resolved_context = context
            
            context_summary = self.resolver.format_context_summary(resolved_context)
            logger.info(f"Context: {context_summary}")
            
            # Step 2: Build prompt with domain hints
            print(f"\n📋 Step 2: Building prompt with {len(domain_hints or [])} domain hints...")
            prompt = self._build_prompt_with_hints(query, resolved_context, domain_hints or [])
            
            print("\n🧠 LLM Input Prompt:")
            print("-" * 80)
            print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
            print("-" * 80)
            
            # Step 3: Generate SQL with LLM
            print("\n⚙️ Step 3: Generating SQL with LLM...")
            sql_query = self._generate_sql_from_prompt(prompt)
            
            # Fix common SQL syntax errors
            sql_query = sql_query.replace("; LIMIT", " LIMIT").replace(";LIMIT", " LIMIT")
            
            print("\n📝 Generated SQL:")
            print("-" * 80)
            print(sql_query)
            print("-" * 80)
            logger.info(f"Generated SQL: {sql_query}")
            
            # Step 4: Execute query on PostgreSQL
            print("\n⚡ Step 4: Executing query on PostgreSQL...")
            with get_db() as db:
                result = db.execute(text(sql_query))
                rows = result.fetchall()
                columns = result.keys()
                print(f"✅ Query executed successfully! Retrieved {len(rows)} rows")
                
                # Convert to list of dicts
                data = []
                for row in rows:
                    row_dict = {}
                    for col, value in zip(columns, row):
                        row_dict[col] = self._normalize_value(value)
                    data.append(row_dict)
            
            logger.info(f"Query returned {len(data)} rows")
            
            # Handle zero rows
            if len(data) == 0:
                logger.warning("⚠️ SQL query returned 0 rows - no matching data found")
                return {
                    "agent": "database",
                    "sql_query": sql_query,
                    "data": [],
                    "row_count": 0,
                    "analysis": self._get_no_data_message(),
                    "data_source": "postgres",
                    "status": "success_no_data"
                }
            
            # Step 5: Generate analysis
            print("\n📊 Step 5: Generating analysis from results...")
            analysis = self.analyze_results(query, data, sql_query)
            
            print(f"\n✅ Database Agent Complete: {len(data)} rows returned")
            print("="*80)
            
            return {
                "agent": "database",
                "sql_query": sql_query,
                "data": data,
                "row_count": len(data),
                "columns": list(columns),
                "context_summary": context_summary,
                "analysis": analysis,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Database query failed: {e}")
            return {
                "agent": "database",
                "error": str(e),
                "sql_query": sql_query if 'sql_query' in locals() else "Query generation failed",
                "status": "failed",
                "data": [],
                "analysis": f"Query execution failed: {str(e)}"
            }
    
    def _build_prompt_with_hints(
        self, 
        query: str, 
        resolved_context: Dict[str, Any],
        domain_hints: List[Dict[str, Any]]
    ) -> str:
        """
        Build comprehensive SQL generation prompt using:
        - Base prompt from context_resolver
        - Domain expert hints (schemas, formulas, join patterns)
        """
        # Get base prompt from context resolver
        base_prompt = self.resolver.get_sql_generation_prompt(query, resolved_context)
        
        # If no domain hints, return base prompt
        if not domain_hints:
            return base_prompt
        
        # Build domain hints section
        hints_section = "\n\n=== DOMAIN EXPERT HINTS ===\n"
        hints_section += "\n⚠️ CRITICAL JOIN ORDER: Always define tables BEFORE referencing them!\n"
        hints_section += "Example: FROM sales s JOIN product_hierarchy ph ... JOIN metrics m ON m.product = ph.product\n"
        hints_section += "(Define ph before using ph.product in JOIN conditions)\n\n"
        
        for hint in domain_hints:
            agent_name = hint.get("agent", "unknown").upper()
            hints_section += f"\n--- {agent_name} AGENT HINTS ---\n"
            
            # Add table schema if provided
            if hint.get("table_schema"):
                hints_section += f"\nTable Schema:\n{hint['table_schema']}\n"
            
            # Add key columns if provided
            if hint.get("key_columns"):
                hints_section += "\nKey Columns:\n"
                for col, desc in hint["key_columns"].items():
                    hints_section += f"  - {col}: {desc}\n"
            
            # Add join patterns if provided
            if hint.get("join_patterns"):
                hints_section += f"\nJoin Patterns:\n{hint['join_patterns']}\n"
            
            # Add formulas if provided
            if hint.get("formulas"):
                hints_section += "\nRelevant Formulas:\n"
                for formula in hint["formulas"]:
                    if isinstance(formula, dict):
                        hints_section += f"  • {formula.get('name', 'Formula')}: {formula.get('sql', formula.get('description', ''))}\n"
                    else:
                        hints_section += f"  • {formula}\n"
            
            # Add time context if provided
            if hint.get("time_context"):
                hints_section += f"\nTime Context:\n{hint['time_context']}\n"
            
            # Add detected filters if provided
            if hint.get("detected_locations"):
                locs = hint["detected_locations"]
                if locs.get("filters"):
                    hints_section += f"\nDetected Location Filters:\n"
                    for f in locs["filters"]:
                        hints_section += f"  - {f}\n"
        
        # Insert hints before the final instruction
        return base_prompt + hints_section
    
    def _generate_sql_from_prompt(self, prompt: str) -> str:
        """Generate SQL query using LLM"""
        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500  
        )
        
        sql_query = response.choices[0].message.content.strip()
        
        # Clean up the query
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        # Add LIMIT if not present
        if "LIMIT" not in sql_query.upper():
            sql_query += " LIMIT 50"
        
        return sql_query
    
    def _get_no_data_message(self) -> str:
        """Return standard no-data message"""
        return """No data found for your query. This could be because:

• The time period you mentioned doesn't have available data
• The product, location, or event name doesn't exist in our records
• The region name might be misspelled (available regions: northeast, southeast, midwest, west, southwest)
• No records match all your search criteria

💡 Suggestions:
- Try a different time period
- Check if the product or location name is spelled correctly
- Use broader search terms
- Try asking about a different region or time range"""

    def query_database(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Backward-compatible method - calls query_with_hints without domain hints.
        
        For the clean architecture, use query_with_hints() with domain hints instead.
        """
        return self.query_with_hints(query=user_query, context=context, domain_hints=[])
    
    def _generate_sql_with_context(self, user_query: str, resolved_context: Dict[str, Any]) -> str:
        """
        Generate SQL query using LLM with full context from Azure Search + Gremlin
        
        This replaces the old _generate_sql_query method that used hardcoded schema
        """
        # Get comprehensive prompt with all context
        prompt = self.resolver.get_sql_generation_prompt(user_query, resolved_context)
        return self._generate_sql_from_prompt(prompt)
    
    def _generate_sql_query(self, user_query: str, context: Dict[str, Any] = None) -> str:
        """Deprecated - use query_with_hints instead"""
        logger.warning("Using deprecated _generate_sql_query method - consider using query_with_hints")
        resolved_context = self.resolver.resolve_query_context(user_query)
        return self._generate_sql_with_context(user_query, resolved_context)
    
    def query_database_for_chart(
        self, 
        user_query: str, 
        chart_type: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate and execute SQL optimized for specific chart type"""
        try:
            # Resolve context first
            resolved_context = self.resolver.resolve_query_context(user_query)
            
            # Generate chart-specific SQL with context
            sql_query = self._generate_chart_specific_sql(user_query, chart_type, resolved_context)
            logger.info(f"📊 Chart-specific SQL ({chart_type}): {sql_query}")
            
            # Execute query
            with get_db() as db:
                result = db.execute(text(sql_query))
                rows = result.fetchall()
                columns = result.keys()
                
                # Convert to clean data
                data = []
                for row in rows:
                    row_dict = {}
                    for col, value in zip(columns, row):
                        row_dict[col] = self._normalize_value(value)
                    data.append(row_dict)
            
            logger.info(f"✅ Retrieved {len(data)} rows optimized for {chart_type}")
            
            return {
                "agent": "database",
                "sql_query": sql_query,
                "data": data,
                "row_count": len(data),
                "columns": list(columns),
                "chart_type": chart_type,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Chart-specific query failed: {e}")
            return {
                "agent": "database",
                "error": str(e),
                "status": "failed",
                "data": []
            }
    
    def _generate_chart_specific_sql(
        self, 
        user_query: str, 
        chart_type: str,
        resolved_context: Dict[str, Any]
    ) -> str:
        """Generate SQL query optimized for specific chart type with full context"""
        
        # Chart type requirements
        chart_requirements = {
            "PieChart": "Need 1 category field and 1 numeric field. Use GROUP BY for aggregation.",
            "BarChart": "Need 1-2 category fields and 1-3 numeric fields. Limit to top 20 rows.",
            "LineChart": "Need 1 time/sequence field and 1-3 numeric trend fields. Order by time.",
            "AreaChart": "Need 1 time field and 1-3 numeric fields for cumulative trends.",
            "ScatterChart": "Need 2 numeric fields (X and Y axis). Include labels if available.",
            "GeoChart": "Need location field (state/region) and 1 numeric field. Aggregate by location.",
            "Table": "Return all relevant fields with proper formatting.",
            "Histogram": "Need 1 numeric field for distribution analysis.",
            "ColumnChart": "Similar to BarChart but for vertical orientation."
        }
        
        requirement = chart_requirements.get(chart_type, "Return relevant data")
        
        # Get base context prompt from resolver
        base_prompt = self.resolver.get_sql_generation_prompt(user_query, resolved_context)
        
        # Enhance with chart-specific requirements
        chart_prompt = f"""
{base_prompt}

CHART-SPECIFIC REQUIREMENTS FOR {chart_type}:
{requirement}

CHART-SPECIFIC GUIDELINES:
- For PieChart: SELECT category_field, SUM(metric) AS value ... GROUP BY category_field LIMIT 10
- For LineChart: SELECT date_field, SUM(metric) AS value ... ORDER BY date_field LIMIT 50
- For BarChart: SELECT category_field, SUM(metric) AS value ... GROUP BY category_field ORDER BY value DESC LIMIT 20
- For GeoChart: SELECT state, SUM(m.metric) AS value FROM metrics m JOIN location l ON m.location = l.location ... GROUP BY state
- For ScatterChart: SELECT numeric_field_1, numeric_field_2 LIMIT 100
- Always use appropriate aggregation (SUM, AVG, COUNT)
- Always include LIMIT clause
- Use clear field aliases (AS category, AS value, AS date)

Generate the SQL query optimized for {chart_type}:
"""

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": chart_prompt}
            ],
            temperature=0.1,
            max_tokens=1200  # Increased for chart-specific queries (was 400)
        )
        
        sql_query = response.choices[0].message.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        # Ensure LIMIT exists
        if "LIMIT" not in sql_query.upper():
            if chart_type == "PieChart":
                sql_query += " LIMIT 10"
            elif chart_type in ["BarChart", "ColumnChart"]:
                sql_query += " LIMIT 20"
            elif chart_type == "LineChart":
                sql_query += " LIMIT 50"
            elif chart_type == "ScatterChart":
                sql_query += " LIMIT 100"
            else:
                sql_query += " LIMIT 50"
        
        return sql_query

    def _normalize_value(self, value: Any) -> Any:
        """Convert database values into JSON-serializable primitives"""
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if isinstance(value, Decimal):
            numeric_value = float(value)
            return int(numeric_value) if numeric_value.is_integer() else numeric_value
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)
    
    def analyze_results(self, user_query: str, data: List[Dict], sql_query: str) -> str:
        """Generate natural language answer from query results - NEVER FABRICATE DATA"""
        try:
            # CRITICAL: If no data, return immediately - DO NOT let LLM fabricate
            if not data or len(data) == 0:
                return """No data found for your query. This could be because:

• The time period you mentioned doesn't have available data
• The product, location, or event name doesn't exist in our records  
• The region name might be misspelled (available regions: Northeast, Southeast, Midwest, West, Southwest)
• No records match all your search criteria

💡 Suggestions:
- Try a different time period
- Check if the product or location name is spelled correctly
- Use broader search terms
- Try asking about a different region or time range"""
            
            # Format data for LLM
            data_summary = f"Query returned {len(data)} rows.\\n\\nSample data:\\n"
            for i, row in enumerate(data[:5]):
                data_summary += f"\\nRow {i+1}: {row}"
            
            prompt = f"""User asked: {user_query}

SQL Query executed:
{sql_query}

Results:
{data_summary}

CRITICAL INSTRUCTIONS:
1. ONLY analyze the ACTUAL data shown above - Do NOT fabricate or invent any additional data.

2. Answer ALL parts of the user's question, not just the first part:
   - If they ask "what is the impact AND how should we adjust ordering" → Answer BOTH parts!
   - If they ask "what decreased AND how to prevent waste" → Provide BOTH analysis AND specific recommendations!
   - Multi-part questions REQUIRE multi-part answers!

3. For ORDERING/INVENTORY questions, provide SPECIFIC actionable recommendations:
   - If demand_change_pct shows -15%, recommend: "Reduce orders by approximately 15% to prevent waste"
   - If forecasted_demand is 800 and normal_demand is 1000, say: "Reduce ordering from normal 1000 units to ~800 units"
   - If there's a "recommended_order" column in results, use those exact numbers
   - Calculate specific quantities: "Order 850 units instead of 1000 units"
   
4. For WASTE PREVENTION questions (CRITICAL - Q3 type):
   - ALWAYS address BOTH demand change AND waste prevention
   - If there's daily_sales_velocity, current_stock, or days_to_expiry data, analyze it
   - If there's potential_waste_units or shelf_life_loss, explain the risk
   - Provide SPECIFIC ordering advice: "Reduce order by X%, monitor stock daily, plan for faster turnover"
   - Explain lead time adjustments: "Order closer to delivery dates" or "Use smaller, more frequent orders"
   - If shelf life data exists: "Current stock of X units with Y days shelf life and Z daily sales = potential waste"
   
5. For DIVERSIFICATION questions:
   - List the top-selling products/categories from the data
   - Suggest which product categories to stock more of
   - Provide specific product recommendations

6. Include specific numbers and trends from the results.

Provide a complete, actionable answer addressing EVERY part of the user's question."""

            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a supply chain analyst. Provide insights ONLY from actual database results. NEVER fabricate data or invent examples. If no data exists, say so clearly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature to reduce hallucination
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Result analysis failed: {e}")
            return f"Found {len(data)} records. SQL query: {sql_query}"
