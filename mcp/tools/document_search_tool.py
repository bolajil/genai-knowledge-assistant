from typing import Dict, Any, List, Sequence
from mcp.server.models import Tool
from mcp.types import TextContent
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class DocumentSearchTool:
    def __init__(self, query_function=None):
        self.name = "document_search"
        self.description = "Search through your indexed document repositories using existing FAISS indexes"
        self.query_function = query_function
        
    def get_tool_definition(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for documents"
                    },
                    "index_name": {
                        "type": "string", 
                        "description": "Name of the FAISS index to search"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to return",
                        "default": 5
                    }
                },
                "required": ["query", "index_name"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        try:
            query = arguments.get("query", "")
            index_name = arguments.get("index_name", "")
            top_k = arguments.get("top_k", 5)
            
            if not self.query_function:
                return [TextContent(
                    type="text",
                    text="❌ Document search function not available"
                )]
            
            # Use your existing query_index function
            results = self.query_function(query, index_name, top_k)
            
            if not results:
                return [TextContent(
                    type="text",
                    text=f"🔍 No results found for query: '{query}' in index '{index_name}'"
                )]
            
            formatted_results = self._format_search_results(results, query, index_name)
            return [TextContent(
                type="text",
                text=formatted_results
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Document search error: {str(e)}"
            )]
    
    def _format_search_results(self, results: List[str], query: str, index_name: str) -> str:
        formatted = f"🔍 **Search Results for '{query}' in '{index_name}'**\n\n"
        
        for i, result in enumerate(results, 1):
            preview = result[:300] + ("..." if len(result) > 300 else "")
            formatted += f"**📄 Result {i}:**\n{preview}\n\n"
            
        formatted += f"Found {len(results)} relevant documents."
        return formatted
