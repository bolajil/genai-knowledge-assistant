from typing import Dict, Any, Sequence, List
from mcp.server.models import Tool
from mcp.types import TextContent
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class KnowledgeRetrieverTool:
    def __init__(self, query_function=None, chat_function=None):
        self.name = "knowledge_retriever"
        self.description = "Advanced knowledge retrieval with context-aware responses"
        self.query_function = query_function
        self.chat_function = chat_function
        
    def get_tool_definition(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Knowledge query or question"
                    },
                    "index_name": {
                        "type": "string",
                        "description": "Index to search in"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["search", "chat", "summarize", "explain"],
                        "description": "Retrieval mode"
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "claude", "deepseek", "mistral", "anthropic"],
                        "description": "LLM provider to use",
                        "default": "openai"
                    }
                },
                "required": ["query", "index_name", "mode"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        try:
            query = arguments.get("query", "")
            index_name = arguments.get("index_name", "")
            mode = arguments.get("mode", "search")
            provider = arguments.get("provider", "openai")
            
            if mode == "search":
                return await self._search_mode(query, index_name)
            elif mode == "chat":
                return await self._chat_mode(query, index_name, provider)
            elif mode == "summarize":
                return await self._summarize_mode(query, index_name, provider)
            elif mode == "explain":
                return await self._explain_mode(query, index_name, provider)
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Unknown mode: {mode}"
                )]
                
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Knowledge retrieval error: {str(e)}"
            )]
    
    async def _search_mode(self, query: str, index_name: str) -> Sequence[TextContent]:
        """Simple search without LLM processing"""
        if not self.query_function:
            return [TextContent(
                type="text",
                text="❌ Search function not available"
            )]
        
        results = self.query_function(query, index_name, 3)
        
        if not results:
            return [TextContent(
                type="text",
                text=f"🔍 No results found for '{query}' in '{index_name}'"
            )]
        
        formatted = f"🔍 **Search Results for '{query}':**\n\n"
        for i, result in enumerate(results, 1):
            preview = result[:200] + ("..." if len(result) > 200 else "")
            formatted += f"**Result {i}:**\n{preview}\n\n"
        
        return [TextContent(type="text", text=formatted)]
    
    async def _chat_mode(self, query: str, index_name: str, provider: str) -> Sequence[TextContent]:
        """Interactive chat with context"""
        if not self.chat_function:
            return [TextContent(
                type="text",
                text="❌ Chat function not available"
            )]
        
        try:
            # Import the get_chat_chain function
            from app.utils.chat_orchestrator import get_chat_chain
            
            chain = get_chat_chain(provider=provider, index_name=index_name)
            response = chain.invoke({"input": query})
            
            # Handle different response formats
            if hasattr(response, "content"):
                answer = response.content
            elif isinstance(response, dict) and "answer" in response:
                answer = response["answer"]
            elif isinstance(response, str):
                answer = response
            else:
                answer = str(response)
            
            formatted = f"💬 **Chat Response ({provider}):**\n\n{answer}"
            
            return [TextContent(type="text", text=formatted)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Chat mode error: {str(e)}"
            )]
    
    async def _summarize_mode(self, query: str, index_name: str, provider: str) -> Sequence[TextContent]:
        """Summarization with context"""
        summary_query = f"Please provide a comprehensive summary of: {query}"
        return await self._chat_mode(summary_query, index_name, provider)
    
    async def _explain_mode(self, query: str, index_name: str, provider: str) -> Sequence[TextContent]:
        """Detailed explanation with context"""
        explain_query = f"Please explain in detail: {query}"
        return await self._chat_mode(explain_query, index_name, provider)
