"""
Agents Package - Clean Architecture
====================================

All agents are DOMAIN EXPERTS that provide hints and context.
ONLY DatabaseAgent executes SQL queries.

Flow:
1. Orchestrator receives query
2. Detects which domains are relevant
3. Collects hints from domain expert agents
4. Passes combined hints to DatabaseAgent
5. DatabaseAgent generates and executes single SQL
6. Returns results for synthesis
"""

from typing import Dict, Any, List

from core.logger import logger

# Domain Expert Agents (provide hints, NO SQL execution)
from .sales_agent import SalesAgent, sales_agent
from .metrics_agent import MetricsAgent, metrics_agent
from .weather_agent import WeatherAgent, weather_agent
from .events_agent import EventsAgent, events_agent
from .inventory_agent import InventoryAgent, inventory_agent
from .location_agent import LocationAgent, location_agent

# SQL Executor Agent (ONLY agent that executes SQL)
from .database_agent import DatabaseAgent

# Visualization (generates charts from data)
from .visualization_agent import VisualizationAgent


class AgentController:
    """
    Agent Controller - Orchestrates Domain Experts
    
    Clean Architecture Pattern:
    - Domain experts (Sales, Metrics, Weather, Events, Inventory, Location)
      provide hints about their domain: schemas, formulas, join patterns
    - DatabaseAgent is the ONLY agent that executes SQL
    - Orchestrator collects hints and passes to DatabaseAgent
    """
    
    def __init__(self):
        # Domain Expert Agents (NO SQL execution)
        self.sales_agent = SalesAgent()
        self.metrics_agent = MetricsAgent()
        self.weather_agent = WeatherAgent()
        self.events_agent = EventsAgent()
        self.inventory_agent = InventoryAgent()
        self.location_agent = LocationAgent()
        
        # SQL Executor (ONLY agent that executes SQL)
        self.database_agent = DatabaseAgent()
        
        # Visualization Agent
        self.visualization_agent = VisualizationAgent()
        
        self.domain_agents = [
            self.sales_agent,
            self.metrics_agent,
            self.weather_agent,
            self.events_agent,
            self.inventory_agent,
            self.location_agent
        ]
        
        logger.info("✅ AgentController initialized with clean architecture")
        logger.info("   📊 6 Domain Expert Agents (provide hints)")
        logger.info("   🗄️ 1 Database Agent (executes SQL)")
        logger.info("   📈 1 Visualization Agent (generates charts)")
    
    def collect_domain_hints(self, query: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Collect hints from all relevant domain experts.
        
        This method asks each domain expert if they can handle the query,
        and if so, collects their domain-specific hints.
        
        Args:
            query: User's natural language query
            context: Resolved context from Azure Search + Gremlin
            
        Returns:
            List of hint dictionaries from relevant domain experts
        """
        hints = []
        
        for agent in self.domain_agents:
            try:
                if agent.can_handle(query):
                    agent_hints = agent.get_domain_hints(query, context)
                    hints.append(agent_hints)
                    logger.info(f"   ↳ {agent_hints.get('agent', 'unknown')} agent provided hints")
            except Exception as e:
                logger.warning(f"⚠️ Error collecting hints from {agent.__class__.__name__}: {e}")
        
        if not hints:
            logger.info("   ↳ No domain-specific hints - using general query")
        
        return hints
    
    def get_active_domains(self, query: str) -> List[str]:
        """Return list of domains that can handle this query"""
        active = []
        for agent in self.domain_agents:
            try:
                if agent.can_handle(query):
                    active.append(agent.__class__.__name__.replace("Agent", "").lower())
            except:
                pass
        return active
    
    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process query using clean architecture flow.
        
        Flow:
        1. Collect domain hints from relevant experts
        2. Pass hints to DatabaseAgent
        3. DatabaseAgent generates and executes SQL
        4. Return results
        """
        try:
            logger.info(f"🔄 Processing query: {query[:50]}...")
            
            # Step 1: Collect domain hints
            domain_hints = self.collect_domain_hints(query, context)
            active_domains = [h.get("agent", "unknown") for h in domain_hints]
            logger.info(f"📋 Active domains: {active_domains}")
            
            # Step 2: Query database with hints
            db_result = self.database_agent.query_with_hints(
                query=query,
                context=context,
                domain_hints=domain_hints
            )
            
            # Step 3: Prepare response
            if db_result.get("status") == "success":
                answer = db_result.get("analysis", "Query executed successfully.")
            else:
                answer = db_result.get("error", "Unable to process query.")
            
            return {
                "query": query,
                "answer": answer,
                "sql_query": db_result.get("sql_query"),
                "data": db_result.get("data", []),
                "row_count": db_result.get("row_count", 0),
                "active_domains": active_domains,
                "status": db_result.get("status", "success")
            }
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            return {
                "error": str(e),
                "status": "failed",
                "answer": "I encountered an error processing your query. Please try rephrasing."
            }


# Global controller instance
agent_controller = AgentController()


# Export all
__all__ = [
    # Domain Expert Agents
    "SalesAgent",
    "MetricsAgent", 
    "WeatherAgent",
    "EventsAgent",
    "InventoryAgent",
    "LocationAgent",
    
    # SQL Executor Agent
    "DatabaseAgent",
    
    # Visualization Agent
    "VisualizationAgent",
    
    # Controller
    "AgentController",
    "agent_controller",
    
    # Global instances
    "sales_agent",
    "metrics_agent",
    "weather_agent",
    "events_agent",
    "inventory_agent",
    "location_agent"
]
agent_controller = AgentController()
