import asyncio
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
import logging

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import MCP tools
from .tools.document_search_tool import DocumentSearchTool
from .tools.content_analyzer_tool import ContentAnalyzerTool
from .tools.knowledge_retriever_tool import KnowledgeRetrieverTool
from .logger import mcp_logger

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, query_function=None, chat_function=None, index_root=None, user=None):
        """Initialize MCP client with your existing functions
        
        Args:
            query_function: Function to query the knowledge base
            chat_function: Function to interact with the chat model
            index_root: Root directory for indexes
            user: User information for logging
        """
        self.tools = {
            "document_search": DocumentSearchTool(query_function),
            "content_analyzer": ContentAnalyzerTool(index_root),
            "knowledge_retriever": KnowledgeRetrieverTool(query_function, chat_function)
        }
        
        self.user = user if user else {"username": "system", "role": "system"}
        
        # Register the tools with the MCP logger
        for tool_name, tool_instance in self.tools.items():
            tool_def = tool_instance.get_tool_definition()
            mcp_logger.register_tool(
                name=tool_def.name,
                description=tool_def.description,
                category=self._get_tool_category(tool_name)
            )
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available MCP tools"""
        tool_list = []
        for tool_name, tool_instance in self.tools.items():
            tool_def = tool_instance.get_tool_definition()
            tool_list.append({
                "name": tool_def.name,
                "description": tool_def.description,
                "schema": tool_def.inputSchema,
                "category": self._get_tool_category(tool_name)
            })
        return tool_list
    
    def _get_tool_category(self, tool_name: str) -> str:
        categories = {
            "document_search": "🔍 Search & Retrieval",
            "content_analyzer": "📊 Analytics & Insights", 
            "knowledge_retriever": "🧠 AI-Powered Knowledge"
        }
        return categories.get(tool_name, "🔧 General")
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a specific MCP tool"""
        if tool_name not in self.tools:
            # Log failed tool execution
            mcp_logger.log_operation(
                operation="TOOL_EXECUTION",
                username=self.user.get("username", "system") if isinstance(self.user, dict) else self.user.username,
                user_role=self.user.get("role", "system") if isinstance(self.user, dict) else self.user.role.value,
                status="failed",
                tool_name=tool_name,
                details={"error": f"Tool '{tool_name}' not found", "arguments": str(arguments)}
            )
            return f"❌ Tool '{tool_name}' not found"
        
        start_time = time.time()
        try:
            tool_instance = self.tools[tool_name]
            result = await tool_instance.execute(arguments)
            execution_time = time.time() - start_time
            
            # Log successful tool execution
            mcp_logger.log_operation(
                operation="TOOL_EXECUTION",
                username=self.user.get("username", "system") if isinstance(self.user, dict) else self.user.username,
                user_role=self.user.get("role", "system") if isinstance(self.user, dict) else self.user.role.value,
                status="success",
                tool_name=tool_name,
                duration=execution_time,
                details={"arguments": str(arguments), "result_type": type(result).__name__}
            )
            
            return result[0].text if result else "No result returned"
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed tool execution
            mcp_logger.log_operation(
                operation="TOOL_EXECUTION",
                username=self.user.get("username", "system") if isinstance(self.user, dict) else self.user.username,
                user_role=self.user.get("role", "system") if isinstance(self.user, dict) else self.user.role.value,
                status="failed",
                tool_name=tool_name,
                duration=execution_time,
                details={"error": str(e), "arguments": str(arguments)}
            )
            
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return f"❌ Error executing '{tool_name}': {str(e)}"
    
    async def smart_query(self, user_input: str, context: Optional[Dict] = None) -> str:
        """Intelligently route queries to appropriate tools"""
        user_input_lower = user_input.lower()
        
        # Intent detection
        if any(keyword in user_input_lower for keyword in ['search', 'find', 'look for', 'retrieve']):
            # Simple document search
            search_terms = self._extract_search_terms(user_input)
            index_name = context.get("selected_index") if context else None
            
            if not index_name:
                return "❌ Please select an index first"
                
            return await self.execute_tool("document_search", {
                "query": search_terms,
                "index_name": index_name,
                "top_k": 5
            })
        
        elif any(keyword in user_input_lower for keyword in ['analyze', 'analysis', 'stats', 'health', 'compare']):
            # Content analysis
            analysis_type = self._determine_analysis_type(user_input)
            index_name = context.get("selected_index") if context else None
            
            if not index_name:
                return "❌ Please select an index first"
                
            return await self.execute_tool("content_analyzer", {
                "index_name": index_name,
                "analysis_type": analysis_type
            })
        
        elif any(keyword in user_input_lower for keyword in ['explain', 'summarize', 'chat', 'ask']):
            # AI-powered knowledge retrieval
            mode = self._determine_retrieval_mode(user_input)
            index_name = context.get("selected_index") if context else None
            provider = context.get("selected_provider", "openai") if context else "openai"
            
            if not index_name:
                return "❌ Please select an index first"
                
            return await self.execute_tool("knowledge_retriever", {
                "query": user_input,
                "index_name": index_name,
                "mode": mode,
                "provider": provider
            })
        
        else:
            return self._generate_help_message()
    
    def _extract_search_terms(self, user_input: str) -> str:
        """Extract search terms from user input"""
        stop_words = ['search', 'find', 'look', 'for', 'retrieve', 'get', 'show', 'me']
        words = user_input.lower().split()
        search_words = [w for w in words if w not in stop_words and len(w) > 2]
        return ' '.join(search_words) or user_input
    
    def _determine_analysis_type(self, user_input: str) -> str:
        """Determine analysis type from user input"""
        if any(word in user_input.lower() for word in ['health', 'check', 'status']):
            return 'health'
        elif any(word in user_input.lower() for word in ['stats', 'statistics', 'metrics']):
            return 'statistics'
        elif any(word in user_input.lower() for word in ['compare', 'comparison', 'vs']):
            return 'comparison'
        else:
            return 'summary'
    
    def _determine_retrieval_mode(self, user_input: str) -> str:
        """Determine retrieval mode from user input"""
        if any(word in user_input.lower() for word in ['explain', 'explanation', 'detail']):
            return 'explain'
        elif any(word in user_input.lower() for word in ['summarize', 'summary', 'overview']):
            return 'summarize'
        elif any(word in user_input.lower() for word in ['chat', 'discuss', 'conversation']):
            return 'chat'
        else:
            return 'search'
    
    def _generate_help_message(self) -> str:
        return """🤖 **MCP Assistant Help**

I can help you with:

🔍 **Document Search**
- "Search for AWS security policies"
- "Find documents about machine learning"

📊 **Content Analysis** 
- "Analyze my_index repository"
- "Show health check for my_index"
- "Compare indexes"

🧠 **AI-Powered Knowledge**
- "Explain cloud computing concepts"
- "Summarize the security documentation"
- "Chat about AWS best practices"

💡 **Tips:**
- Select an index first
- Be specific in your queries
- Try different LLM providers for varied responses
        """
