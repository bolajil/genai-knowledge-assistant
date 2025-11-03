# app/utils/langgraph_agent.py
"""
Enhanced LangGraph Agent with Multiple Tools
Provides autonomous reasoning and multi-step query processing
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain_community.chat_models import ChatOpenAI

try:
    from langgraph.prebuilt import create_react_agent
except ImportError:
    from langgraph.prebuilt import create_agent_executor as create_react_agent

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"
INDEX_ROOT = "data/faiss_index"


class EnhancedLangGraphAgent:
    """Enhanced LangGraph agent with multiple tools and better error handling"""
    
    def __init__(self, 
                 index_names: List[str],
                 llm_model: str = "gpt-3.5-turbo",
                 temperature: float = 0.1,
                 max_iterations: int = 5):
        """
        Initialize enhanced agent
        
        Args:
            index_names: List of FAISS index names to search
            llm_model: OpenAI model name
            temperature: LLM temperature
            max_iterations: Max reasoning iterations
        """
        self.index_names = index_names
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.embeddings = None
        self.agent = None
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize embeddings and agent"""
        try:
            # Load embeddings
            embed_path = Path(EMBED_MODEL)
            if embed_path.exists():
                self.embeddings = HuggingFaceEmbeddings(model_name=str(embed_path))
            else:
                # Fallback to default model
                self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            
            # Create LLM
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found, agent may not work")
            
            llm = ChatOpenAI(
                model=self.llm_model,
                temperature=self.temperature,
                api_key=api_key
            )
            
            # Build tools
            tools = self._build_tools()
            
            # Create agent
            self.agent = create_react_agent(llm, tools)
            
            logger.info(f"Enhanced LangGraph agent initialized with {len(tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangGraph agent: {e}")
            self.agent = None
    
    def _build_tools(self) -> List[Tool]:
        """Build tools for the agent"""
        tools = []
        
        # Document retrieval tools for each index
        for index_name in self.index_names:
            tool = Tool(
                name=f"Search_{index_name}",
                func=lambda q, idx=index_name: self._retrieve_docs(q, idx),
                description=f"Search documents in {index_name} index. Use this to find information from {index_name} documents."
            )
            tools.append(tool)
        
        # Multi-index search tool
        if len(self.index_names) > 1:
            tools.append(Tool(
                name="SearchAllIndexes",
                func=self._search_all_indexes,
                description="Search across all available document indexes. Use when you need comprehensive information from multiple sources."
            ))
        
        # Comparison tool
        if len(self.index_names) > 1:
            tools.append(Tool(
                name="CompareDocuments",
                func=self._compare_documents,
                description="Compare information from different document sources. Provide the comparison topic as input."
            ))
        
        return tools
    
    def _retrieve_docs(self, question: str, index_name: str, top_k: int = 4) -> str:
        """Retrieve documents from specific index"""
        try:
            index_path = Path(INDEX_ROOT) / index_name
            logger.info(f"Attempting to load index from: {index_path}")
            
            if not index_path.exists():
                error_msg = f"Index path does not exist: {index_path}"
                logger.error(error_msg)
                return f"Index {index_name} not found at {index_path}. Please verify the index exists."
            
            # Check if index files exist
            index_file = index_path / "index.faiss"
            if not index_file.exists():
                error_msg = f"FAISS index file not found: {index_file}"
                logger.error(error_msg)
                return f"FAISS index file missing in {index_name}. The index may not be properly created."
            
            logger.info(f"Loading FAISS index from {index_path}")
            db = FAISS.load_local(
                str(index_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            logger.info(f"Searching for: {question[:100]}")
            docs = db.similarity_search(question, k=top_k)
            
            if not docs:
                return f"No relevant documents found in {index_name} for query: {question[:100]}"
            
            logger.info(f"Found {len(docs)} documents in {index_name}")
            
            # Format results
            results = []
            for i, doc in enumerate(docs, 1):
                content = doc.page_content[:500]  # Limit length
                metadata = doc.metadata
                source = metadata.get('source', 'Unknown')
                page = metadata.get('page', 'N/A')
                results.append(f"[{i}] Source: {source}, Page: {page}\n{content}")
            
            return "\n\n".join(results)
            
        except Exception as e:
            error_msg = f"Error retrieving from {index_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error accessing {index_name}: {str(e)}. Please check if the index is properly created and accessible."
    
    def _search_all_indexes(self, question: str) -> str:
        """Search across all indexes"""
        results = []
        for index_name in self.index_names:
            result = self._retrieve_docs(question, index_name, top_k=2)
            results.append(f"=== Results from {index_name} ===\n{result}")
        return "\n\n".join(results)
    
    def _compare_documents(self, topic: str) -> str:
        """Compare information across indexes"""
        results = []
        results.append(f"Comparing information about: {topic}\n")
        
        for index_name in self.index_names:
            result = self._retrieve_docs(topic, index_name, top_k=2)
            results.append(f"\n--- {index_name} ---\n{result}")
        
        return "\n".join(results)
    
    def query(self, question: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """
        Query the agent
        
        Args:
            question: User question
            chat_history: Optional chat history
            
        Returns:
            Dict with response, reasoning steps, and metadata
        """
        if not self.agent:
            return {
                "response": "Agent not initialized. Please check configuration.",
                "error": "Agent initialization failed",
                "steps": []
            }
        
        try:
            # Prepare input
            messages = []
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=question))
            
            # Invoke agent
            result = self.agent.invoke({
                "messages": messages
            })
            
            # Extract response
            if isinstance(result, dict):
                messages_out = result.get("messages", [])
                if messages_out:
                    last_message = messages_out[-1]
                    response = last_message.content if hasattr(last_message, 'content') else str(last_message)
                else:
                    response = str(result)
            else:
                response = str(result)
            
            return {
                "response": response,
                "steps": self._extract_steps(result),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error querying agent: {e}")
            return {
                "response": f"Error processing query: {str(e)}",
                "error": str(e),
                "steps": [],
                "success": False
            }
    
    def _extract_steps(self, result: Any) -> List[Dict[str, str]]:
        """Extract reasoning steps from result"""
        steps = []
        try:
            if isinstance(result, dict):
                messages = result.get("messages", [])
                for msg in messages:
                    if hasattr(msg, 'content'):
                        steps.append({
                            "type": msg.__class__.__name__,
                            "content": msg.content[:200]  # Truncate
                        })
        except Exception as e:
            logger.error(f"Error extracting steps: {e}")
        return steps


# Legacy function for backward compatibility
def retrieve_docs(question: str, index_name: str) -> str:
    """Legacy function for backward compatibility"""
    try:
        embed_path = Path(EMBED_MODEL)
        if embed_path.exists():
            embeddings = HuggingFaceEmbeddings(model_name=str(embed_path))
        else:
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        db = FAISS.load_local(
            f"{INDEX_ROOT}/{index_name}",
            embeddings,
            allow_dangerous_deserialization=True
        )
        docs = db.similarity_search(question, k=4)
        return "\n\n".join([d.page_content for d in docs])
    except Exception as e:
        return f"Error: {str(e)}"


def build_graph(index_name: str, llm):
    """Legacy function for backward compatibility"""
    tools = [
        Tool(
            name="RetrieveDocs",
            func=lambda x: retrieve_docs(x, index_name),
            description="Retrieve relevant document chunks"
        )
    ]
    return create_react_agent(llm=llm, tools=tools)

