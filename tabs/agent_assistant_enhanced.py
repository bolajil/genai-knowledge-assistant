"""
Enhanced Agent Assistant with Improved Document Processing and Structured Output
Integrated with Enterprise-grade Model Context Protocol (MCP)
"""
import streamlit as st
import json
import time
import concurrent.futures
from datetime import datetime
import os
from pathlib import Path
import logging
import sys
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import hashlib
import traceback
import uuid
from functools import lru_cache

# Tooling imports for enterprise actions
from app.mcp.function_calling import FunctionHandler
import app.tools.email_tool  # Ensure email tool registers with FunctionHandler
import base64
import mimetypes
import app.tools.slack_tool  # Ensure Slack tool registers
import app.tools.teams_tool  # Ensure Teams tool registers
from app.auth.enterprise_permissions import enterprise_permissions, PermissionLevel
from app.auth.resource_request_manager import resource_request_manager

# Simple vector manager for index discovery and validation
from utils.simple_vector_manager import get_simple_indexes, get_simple_index_path

# Optional dotenv loading for .env and .env.local
try:
    from dotenv import load_dotenv as _load_dotenv
except Exception:
    _load_dotenv = None

def load_env_files():
    """Load environment variables from .env.local and .env without overriding existing os.environ."""
    try:
        root_dir = Path(__file__).resolve().parents[1]
        candidates = [root_dir / ".env.local", root_dir / ".env"]
        for p in candidates:
            if p.exists():
                if _load_dotenv:
                    _load_dotenv(dotenv_path=p, override=False)
                else:
                    # Minimal parser
                    try:
                        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if "=" in line:
                                k, v = line.split("=", 1)
                                k = k.strip(); v = v.strip().strip('"').strip("'")
                                if k and k not in os.environ:
                                    os.environ[k] = v
                    except Exception:
                        pass
    except Exception:
        pass

def write_env_local(updates: dict, section: str = "Agent Assistant") -> str:
    """Persist updates to .env.local in project root; returns the path written."""
    root_dir = Path(__file__).resolve().parents[1]
    env_path = root_dir / ".env.local"
    # Load existing
    existing = {}
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not line or line.strip().startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
        except Exception:
            pass
    # Merge
    for k, v in updates.items():
        if v is None:
            continue
        existing[k] = str(v)
    # Write
    lines = [f"# {section} - updated by Agent Assistant"]
    for k, v in existing.items():
        special = any(c in v for c in [' ', '#', '"', "'", '='])
        if special:
            v_escaped = v.replace('"', '\\"')
            lines.append(f'{k}="{v_escaped}"')
        else:
            lines.append(f"{k}={v}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(env_path)

# Load environment at module import
load_env_files()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the controller agent and its dependencies
try:
    from app.agents.controller_agent import (
        choose_provider, 
        generate_prompt, 
        execute_agent as execute_controller_agent
    )
    from app.mcp.protocol import ModelContext # Assuming this is the correct path
    CONTROLLER_AGENT_AVAILABLE = True
    logger.info("Successfully imported controller agent components.")
except Exception as e:
    CONTROLLER_AGENT_AVAILABLE = False
    logger.error(f"Controller agent components not available: {e}")
    # Define a dummy ModelContext if it's not available
    class ModelContext:
        def __init__(self):
            self.model_name = "gpt-3.5-turbo"
            self.parameters = {}
        def get_from_memory(self, key): return None
        def save_to_memory(self, key, value): pass
        def add_to_memory(self, key, value): pass
        
# Import centralized vector database provider and Weaviate
try:
    from utils.vector_db_init import get_any_vector_db_provider, VECTOR_DB_AVAILABLE
    from utils.weaviate_manager import get_weaviate_manager
    from utils.weaviate_collection_selector import render_collection_selector, render_backend_selector
    WEAVIATE_UI_AVAILABLE = True
    
    # Get the vector database provider instance
    vector_db_provider = get_any_vector_db_provider()
    weaviate_manager = get_weaviate_manager()
    logger.info("Vector database provider and Weaviate manager initialized successfully")
except Exception as e:
    VECTOR_DB_AVAILABLE = False
    WEAVIATE_UI_AVAILABLE = False
    vector_db_provider = None
    weaviate_manager = None
    logger.error(f"Vector database provider not available: {e}")
    
    # Create fallback functions
    def render_backend_selector(key="backend"):
        return "FAISS (Local Index)"
    def render_collection_selector(key="collection", label="Collection", help_text=""):
        return None

# Try to import the enhanced search utility
try:
    from utils.enhanced_search import get_enhanced_search
    enhanced_search = get_enhanced_search()
    ENHANCED_SEARCH_AVAILABLE = True
    logger.info("Enhanced search utility initialized successfully")
except Exception as e:
    ENHANCED_SEARCH_AVAILABLE = False
    enhanced_search = None
    logger.error(f"Enhanced search utility not available: {e}")

# Try to import MCP components
try:
    from mcp.logger import mcp_logger
    try:
        from mcp.mcp_client import MCPClient
        MCP_AVAILABLE = True
    except ImportError:
        # Create a simple MCPClient class if not available
        class MCPClient:
            def __init__(self, user=None):
                self.user = user
        MCP_AVAILABLE = True  # Still mark as available to use logger
        logging.warning("MCPClient not available, using fallback implementation")
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP components not available. Running in reduced functionality mode.")

# Configuration
class Config:
    MAX_HISTORY_ITEMS = 20
    MAX_FILE_SIZE_MB = 50
    CACHE_SIZE = 128
    DEFAULT_TIMEOUT = 30
    SUPPORTED_FORMATS = ['markdown', 'html', 'json', 'plain_text', 'structured']
    MCP_ENABLED = True  # Enable Model Context Protocol by default
    MCP_LOG_LEVEL = "INFO"
    MCP_TRACE_ID_HEADER = "X-MCP-Trace-ID"
    
# Enhanced data structures
class OutputFormat(Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PLAIN_TEXT = "plain_text"
    STRUCTURED = "structured"
    
class ProcessingMode(Enum):
    STANDARD = "standard"
    ADVANCED = "advanced"
    EXPERT = "expert"

class MCPContextLevel(Enum):
    """Model Context Protocol context tracking levels"""
    NONE = "none"  # No context tracking
    BASIC = "basic"  # Track basic operation info
    DETAILED = "detailed"  # Track detailed context including inputs and outputs
    COMPREHENSIVE = "comprehensive"  # Track comprehensive context with detailed analytics
    COMPLETE = "complete"  # Track complete context with all intermediate states
    
@dataclass
class MCPContext:
    """Model Context Protocol tracking context"""
    trace_id: str  # Unique identifier for the entire operation chain
    operation_id: str  # Unique identifier for this specific operation
    user_id: str  # User identifier
    timestamp: float  # Operation timestamp
    operation_type: str  # Type of operation being performed
    context_level: MCPContextLevel  # Level of context tracking
    parent_operation_id: Optional[str] = None  # Parent operation if this is part of a chain
    metadata: Dict[str, Any] = None  # Additional metadata
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
@dataclass
class ProcessingResult:
    content: str
    metadata: Dict[str, Any]
    sources: List[str]
    processing_time: float
    format_type: OutputFormat
    mcp_context: Optional[MCPContext] = None  # MCP context tracking
    
@dataclass
class DocumentAnalysis:
    word_count: int
    paragraph_count: int
    has_headings: bool
    has_lists: bool
    document_type: str
    key_terms: List[str]
    structure_score: float
    mcp_context: Optional[MCPContext] = None  # MCP context tracking
    security_classification: str = "Internal"  # Document security classification
    content_hash: str = ""  # Hash of the document content for integrity verification
    processing_metadata: Dict[str, Any] = None  # Additional processing metadata
    
    def __post_init__(self):
        if self.processing_metadata is None:
            self.processing_metadata = {}
    

# Initialize global managers
search_manager = None
content_generator = None
mcp_tracker = None
UNIFIED_CONTENT_GENERATOR_AVAILABLE = False  # Global flag for content generator availability
MCP_TRACKER_AVAILABLE = False  # Global flag for MCP tracker availability

# Model Context Protocol tracker for enterprise-grade observability
class MCPTracker:
    """Enterprise-grade Model Context Protocol tracker"""
    
    def __init__(self, user_info=None):
        """Initialize the MCP tracker
        
        Args:
            user_info: Information about the current user
        """
        self.available = MCP_AVAILABLE
        self.client = None
        self.user_info = user_info if user_info else {"username": "system", "role": "system"}
        self.session_id = str(uuid.uuid4())
        
        # Initialize if MCP is available
        if MCP_AVAILABLE:
            try:
                self.client = MCPClient(user=self.user_info)
                logger.info("MCP client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {str(e)}")
                self.available = False
    
    def create_context(self, operation_type: str, context_level: MCPContextLevel = MCPContextLevel.BASIC) -> MCPContext:
        """Create a new MCP context
        
        Args:
            operation_type: Type of operation being performed
            context_level: Level of context tracking
        
        Returns:
            New MCP context object
        """
        trace_id = str(uuid.uuid4())
        operation_id = str(uuid.uuid4())
        timestamp = time.time()
        
        context = MCPContext(
            trace_id=trace_id,
            operation_id=operation_id,
            user_id=self.user_info.get('username', 'unknown'),
            timestamp=timestamp,
            operation_type=operation_type,
            context_level=context_level
        )
        
        # Log the context creation to MCP if available
        if self.available and MCP_AVAILABLE:
            try:
                mcp_logger.log_operation(
                    operation=f"CREATE_CONTEXT_{operation_type.upper()}",
                    username=self.user_info.get('username', 'unknown'),
                    user_role=self.user_info.get('role', 'unknown'),
                    status="success",
                    details={
                        "trace_id": trace_id,
                        "operation_id": operation_id,
                        "context_level": context_level.value
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log MCP context creation: {str(e)}")
        
        return context
    
    def update_context(self, context: MCPContext, metadata: Dict[str, Any]) -> MCPContext:
        """Update an existing MCP context with new metadata
        
        Args:
            context: Existing MCP context
            metadata: New metadata to add
        
        Returns:
            Updated MCP context
        """
        if not context:
            return self.create_context("UNKNOWN")
            
        # Update the context metadata
        if not context.metadata:
            context.metadata = {}
            
        context.metadata.update(metadata)
        
        # Log the context update to MCP if available
        if self.available and MCP_AVAILABLE:
            try:
                mcp_logger.log_operation(
                    operation=f"UPDATE_CONTEXT_{context.operation_type.upper()}",
                    username=context.user_id,
                    user_role=self.user_info.get('role', 'unknown'),
                    status="success",
                    details={
                        "trace_id": context.trace_id,
                        "operation_id": context.operation_id,
                        "metadata_keys": list(metadata.keys())
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log MCP context update: {str(e)}")
        
        return context
    
    def log_operation(self, context: MCPContext, operation: str, status: str = "success", 
                     duration: float = None, details: Dict[str, Any] = None) -> None:
        """Log an operation to MCP
        
        Args:
            context: MCP context
            operation: Operation name
            status: Operation status
            duration: Operation duration in seconds
            details: Operation details
        """
        if not self.available or not MCP_AVAILABLE:
            return
            
        try:
            mcp_logger.log_operation(
                operation=operation,
                username=context.user_id,
                user_role=self.user_info.get('role', 'unknown'),
                status=status,
                duration=duration,
                details={
                    "trace_id": context.trace_id,
                    "operation_id": context.operation_id,
                    **(details or {})
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log MCP operation: {str(e)}")

# Enhanced search and content modules with proper error handling
class SearchResult:
    def __init__(self, content: str, source_name: str, source_type: str, 
                 relevance_score: float = 0.0, metadata: Optional[Dict] = None):
        self.content = content
        self.source_name = source_name
        self.source_type = source_type
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
        
class SearchManager:
    def __init__(self):
        self.search_available = False
        self._initialize_search()
        self.mcp_context = None
        
    def _initialize_search(self):
        try:
            # First try to use the enhanced search utility
            global enhanced_search, ENHANCED_SEARCH_AVAILABLE
            
            if ENHANCED_SEARCH_AVAILABLE and enhanced_search:
                # Define wrapper methods to use enhanced search
                def perform_search(query, knowledge_sources, max_results=5, **kwargs):
                    # Create MCP context if available
                    global mcp_tracker, MCP_TRACKER_AVAILABLE
                    start_time = time.time()
                    mcp_context = None
                    
                    if MCP_TRACKER_AVAILABLE and mcp_tracker:
                        mcp_context = mcp_tracker.create_context(
                            operation_type="ENHANCED_SEARCH", 
                            context_level=MCPContextLevel.DETAILED
                        )
                        mcp_tracker.update_context(mcp_context, {
                            "query": query,
                            "knowledge_sources": knowledge_sources,
                            "max_results": max_results,
                            "additional_params": kwargs
                        })
                    
                    results = []
                    status = "success"
                    error_details = None
                    
                    try:
                        # Use unified retrieval system for all document searches
                        logger.info(f"Using unified retrieval system for query: {query}")
                        
                        # Detect if query has metadata search patterns
                        has_metadata_patterns = any(pattern in query for pattern in ["type:", "date:", "size:", "author:", "category:", "source:"])
                        
                        # Choose search type based on query
                        search_type = "hybrid"
                        if has_metadata_patterns:
                            search_type = "hybrid"  # Use hybrid to combine metadata and vector search
                        
                        # Use unified retrieval system instead of enhanced search
                        try:
                            from utils.unified_document_retrieval import search_documents
                            
                            # Use unified retrieval for each knowledge source
                            for source in knowledge_sources:
                                unified_results = search_documents(query, source, max_results)
                                
                                for result in unified_results:
                                    if not result.get("error"):
                                        results.append(SearchResult(
                                            content=result.get('content', 'No content available'),
                                            source_name=result.get('source', 'Unknown'),
                                            source_type="document",
                                            relevance_score=result.get('relevance_score', 0.0),
                                            metadata=result.get('metadata', {})
                                        ))
                            
                            if results:
                                logger.info(f"Unified retrieval found {len(results)} results")
                                
                        except ImportError:
                            logger.warning("Unified retrieval system not available, falling back to enhanced search")
                        except Exception as e:
                            logger.error(f"Unified retrieval failed: {e}, falling back to enhanced search")
                        
                        # Fallback to enhanced search if unified retrieval fails or no results
                        if not results:
                            search_results = enhanced_search.search(
                                query=query, 
                                max_results=max_results,
                                search_type=search_type,
                                index_name=knowledge_sources[0] if knowledge_sources and len(knowledge_sources) == 1 else None,
                                **kwargs
                            )
                            
                            # Convert to SearchResult objects expected by the agent
                            for result in search_results:
                                results.append(SearchResult(
                                    content=result.content,
                                    source_name=result.source,
                                    source_type="document",
                                    relevance_score=result.relevance,
                                    metadata=result.metadata
                                ))
                            
                    except Exception as e:
                        status = "error"
                        error_details = str(e)
                        logger.error(f"Enhanced search error: {str(e)}")
                        
                        # Final fallback: Return error message
                        results.append(SearchResult(
                            content=f"Search failed: {error_details}. Please try a different query or check if the knowledge source is available.",
                            source_name="System Error",
                            source_type="error",
                            relevance_score=0.0,
                            metadata={}
                        ))
                    
                    # Log to MCP if available
                    if MCP_TRACKER_AVAILABLE and mcp_tracker and mcp_context:
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        # Add result metadata to context
                        mcp_tracker.update_context(mcp_context, {
                            "result_count": len(results),
                            "status": status,
                            "error": error_details
                        })
                        
                        # Log the operation
                        mcp_tracker.log_operation(
                            context=mcp_context,
                            operation="ENHANCED_SEARCH",
                            status=status,
                            duration=duration,
                            details={
                                "query": query,
                                "result_count": len(results)
                            }
                        )
                    
                    return results
                        
                        # Function to format search results for agent consumption
                def format_search_results_for_agent(results):
                    if not results:
                        return "No relevant information found."
                    
                    formatted = "### Relevant Information:\n\n"
                    
                    for i, result in enumerate(results, 1):
                        formatted += f"**Source {i}** (Relevance: {result.relevance_score:.2f}):\n"
                        formatted += f"{result.content}\n\n"
                    
                    return formatted
                
                self.perform_search = perform_search
                self.format_results = format_search_results_for_agent
                self.search_available = True
                logger.info("Search module loaded successfully with enhanced search utility")
                return
            
            # Fall back to legacy search service if centralized provider not available
            try:
                from utils.search_service import SearchService
                from utils.simple_search import SearchResult
                
                # Define wrapper methods to use SearchService with the same interface
                def perform_search(query, knowledge_sources, max_results=5, **kwargs):
                    # Create MCP context if available
                    global mcp_tracker, MCP_TRACKER_AVAILABLE
                    start_time = time.time()
                    mcp_context = None
                    
                    if MCP_TRACKER_AVAILABLE and mcp_tracker:
                        mcp_context = mcp_tracker.create_context(
                            operation_type="SEARCH", 
                            context_level=MCPContextLevel.DETAILED
                        )
                        mcp_tracker.update_context(mcp_context, {
                            "query": query,
                            "knowledge_sources": knowledge_sources,
                            "max_results": max_results,
                            "additional_params": kwargs
                        })
                    
                    # Convert knowledge sources to index names
                    index_names = []
                    for source in knowledge_sources:
                        # Handle the case when permissions['indexes'] is not available
                        available_indexes = ["General", "AWS", "Azure", "Google", "ByLaw_index", "ByLawS2_index"]
                        if source in available_indexes:
                            index_names.append(source)
                    
                    results = []
                    status = "success"
                    error_details = None
                    
                    try:
                        # If we have valid index names, use the SearchService
                        if index_names:
                            results = SearchService.search(
                                query=query,
                                index_names=index_names,
                                max_results=max_results
                            )
                        
                        # If "Web Search" is in the knowledge sources, also search the web
                        elif any(ks.lower().startswith("web") for ks in knowledge_sources):
                            results = SearchService.search_web(
                                query=query,
                                max_results=max_results
                            )
                    except Exception as e:
                        status = "error"
                        error_details = str(e)
                        logger.error(f"Search error: {str(e)}")
                    
                    # Log to MCP if available
                    if MCP_TRACKER_AVAILABLE and mcp_tracker and mcp_context:
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        # Add result metadata to context
                        mcp_tracker.update_context(mcp_context, {
                            "result_count": len(results),
                            "index_names": index_names,
                            "status": status,
                            "error": error_details
                        })
                        
                        # Log the operation
                        mcp_tracker.log_operation(
                            context=mcp_context,
                            operation="VECTOR_SEARCH",
                            status=status,
                            duration=duration,
                            details={
                                "query": query,
                                "result_count": len(results),
                                "knowledge_sources": knowledge_sources,
                                "index_names": index_names,
                                "error": error_details
                            }
                        )
                    
                    return results
                
                def format_results(results):
                    return SearchService.format_results_for_display(
                        results=results,
                        format_type="markdown"
                    )
                
                self.perform_search = perform_search
                self.format_results = format_results
                self.search_available = True
                logger.info("Using new SearchService for enhanced search capabilities")
                
            except ImportError:
                # Fall back to the original implementation
                from utils.simple_search import perform_multi_source_search, format_search_results_for_agent
                self.perform_search = perform_multi_source_search
                self.format_results = format_search_results_for_agent
                self.search_available = True
                logger.info("Search module loaded successfully (using legacy implementation)")
                
        except ImportError as e:
            logger.warning(f"Search module not available: {e}")
            self.perform_search = self._fallback_search
            self.format_results = self._fallback_format
            
    def _fallback_search(self, query: str, knowledge_sources: List[str], 
                        max_results: int = 5, **kwargs) -> List[SearchResult]:
        if "General Knowledge" in knowledge_sources:
            return []
        return [SearchResult(
            content=f"Fallback search result for: {query}",
            source_name="System Fallback",
            source_type="fallback",
            relevance_score=0.3
        )]
        
    def _fallback_format(self, results: List[SearchResult]) -> str:
        if not results:
            return "No search results available."
        formatted = "### Search Results\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"**Result {i}:** {result.content}\n\n"
        return formatted
        
# Initialize search manager
search_manager = SearchManager()

# Function to get vector DB status for display in UI
def get_vector_database_status():
    """Get vector database status for display in system status section"""
    global vector_db_provider, VECTOR_DB_AVAILABLE
    
    # Reinitialize the provider to get the latest status
    try:
        from utils.vector_db_init import get_any_vector_db_provider
        
        # Get the provider instance (will be initialized if not already done)
        provider = get_any_vector_db_provider()
        
        if provider:
            try:
                status, message = provider.get_vector_db_status()
                return status, message
            except Exception as e:
                logger.error(f"Error getting vector DB status: {e}")
                return "Error", f"Failed to check vector DB status: {str(e)}"
        else:
            return "Error", "Vector DB Provider Not Available"
    except Exception as e:
        logger.error(f"Error initializing vector DB provider: {e}")
        return "Error", "No Vector DB Available"

# Enhanced content generation system
class ContentGenerator:
    def __init__(self):
        self.generator_available = False
        self.mcp_context = None
        self._initialize_generator()
        
    def _initialize_generator(self):
        try:
            # First try to import the specialized ByLaws content generator
            try:
                from utils.bylaws_content_generator import (
                    generate_content_with_search_results as bylaws_generate_content,
                    generate_document_summary as bylaws_generate_summary,
                    generate_research_content as bylaws_generate_research
                )
                logger.info("Using specialized ByLaws content generator")
                content_generator_module = "bylaws"
            except ImportError:
                # Fall back to unified content generator
                from utils.unified_content_generator import (
                    generate_content_with_search_results, 
                    generate_document_summary, 
                    generate_research_content
                )
                logger.info("Using standard unified content generator")
                content_generator_module = "unified"
            
            # Wrap the generate_content_with_search_results function with MCP tracking
            def generate_content_with_mcp(query, search_results, operation_type, format_type="markdown", **kwargs):
                # Create MCP context if available
                global mcp_tracker, MCP_TRACKER_AVAILABLE
                start_time = time.time()
                mcp_context = None
                
                if MCP_TRACKER_AVAILABLE and mcp_tracker:
                    mcp_context = mcp_tracker.create_context(
                        operation_type="CONTENT_GENERATION", 
                        context_level=MCPContextLevel.COMPREHENSIVE
                    )
                    mcp_tracker.update_context(mcp_context, {
                        "query": query,
                        "search_results_count": len(search_results),
                        "operation_type": operation_type,
                        "format_type": format_type,
                        "additional_params": kwargs
                    })
                
                # Call the appropriate content generation function
                try:
                    if content_generator_module == "bylaws":
                        # Check if any search results are related to ByLaws
                        has_bylaws = False
                        for result in search_results:
                            if hasattr(result, "source_name") and "bylaw" in result.source_name.lower():
                                has_bylaws = True
                                break
                        
                        if has_bylaws:
                            logger.info("Using ByLaws content generator for ByLaws content")
                            content = bylaws_generate_content(
                                query=query,
                                search_results=search_results,
                                operation_type=operation_type,
                                format_type=format_type,
                                **kwargs
                            )
                        else:
                            content = generate_content_with_search_results(
                                query=query,
                                search_results=search_results,
                                operation_type=operation_type,
                                format_type=format_type,
                                **kwargs
                            )
                    else:
                        content = generate_content_with_search_results(
                            query=query,
                            search_results=search_results,
                            operation_type=operation_type,
                            format_type=format_type,
                            **kwargs
                        )
                    
                    status = "success"
                    error_details = None
                except Exception as e:
                    content = f"Error generating content: {str(e)}"
                    status = "error"
                    error_details = str(e)
                    logger.error(f"Content generation error: {str(e)}")
                
                # Log to MCP if available
                if MCP_TRACKER_AVAILABLE and mcp_tracker and mcp_context:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Add result metadata to context
                    mcp_tracker.update_context(mcp_context, {
                        "content_length": len(content) if content else 0,
                        "status": status,
                        "error": error_details
                    })
                    
                    # Log the operation
                    mcp_tracker.log_operation(
                        context=mcp_context,
                        operation="CONTENT_GENERATION",
                        status=status,
                        duration=duration,
                        details={
                            "query": query,
                            "search_results_count": len(search_results),
                            "content_length": len(content) if content else 0,
                            "operation_type": operation_type,
                            "error": error_details
                        }
                    )
                
                return content
            
            # Set up the content generator methods
            self.generate_content = generate_content_with_mcp
            
            # Set up document summary generator
            if content_generator_module == "bylaws":
                self.generate_summary = bylaws_generate_summary
                self.generate_research = bylaws_generate_research
            else:
                self.generate_summary = generate_document_summary
                self.generate_research = generate_research_content
                
            self.generator_available = True
            # Set global flag for content generator availability
            global UNIFIED_CONTENT_GENERATOR_AVAILABLE
            UNIFIED_CONTENT_GENERATOR_AVAILABLE = True
            logger.info("Content generator loaded successfully")
        except ImportError as e:
            logger.warning(f"Content generator not available: {e}")
            self.generate_content = self._fallback_content
            self.generate_summary = self._fallback_summary
            self.generate_research = self._fallback_research
            
    def _fallback_content(self, task: str, operation: str, 
                         search_results_text: str = "", tone: str = "professional") -> str:
        return f"""## {operation}: {task}

### Analysis
This response addresses your request for {operation.lower()} regarding: {task}

### Content
{search_results_text if search_results_text else "Generated using system knowledge base."}

### Summary
The above content provides a comprehensive overview based on available information.
"""
    
    def _fallback_summary(self, content: str, **kwargs) -> str:
        lines = content.split('\n')[:10]  # First 10 lines
        return f"""## Document Summary

### Key Points
{chr(10).join(f"- {line.strip()}" for line in lines if line.strip())}

### Overview
This summary captures the main elements of the provided content.
"""
    
    def _fallback_research(self, task: str, operation: str, **kwargs) -> str:
        return f"""## Research Report: {task}

### Executive Summary
This research addresses: {task}

### Key Findings
1. Primary focus area identified
2. Relevant context established
3. Actionable insights provided

### Recommendations
Based on the analysis, consider implementing structured approaches to {task.lower()}.
"""

# Define constants
MAX_HISTORY_ITEMS = 10
DEFAULT_KNOWLEDGE_SOURCES = ["Indexed Documents", "Web Search (External)", "Structured Data (External)", "General Knowledge"]

def is_bylaw_query(query):
    """Determine if a query is related to ByLaw content"""
    if not query:
        return False
        
    bylaw_keywords = [
        "board meeting", "director meeting", "quorum", "executive session", 
        "bylaws", "bylaw", "association business", "action outside of meeting",
        "board", "director", "vote", "meeting"
    ]
    
    # Check if any keywords are in the query
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in bylaw_keywords)

def render_agent_assistant(user, permissions, auth_middleware, available_indexes):
    """Main entry point for the Agent Assistant tab"""
    global search_manager, content_generator, mcp_tracker, MCP_TRACKER_AVAILABLE
    
    # Initialize managers if not already done
    if search_manager is None:
        search_manager = SearchManager()
    if content_generator is None:
        content_generator = ContentGenerator()
    
    # Extract user info
    user_name = user.get('name', 'Unknown User') if user else 'Unknown User'
    user_email = user.get('email', 'No email') if user else 'No email'
    # Compute user identifiers and role for permission system
    if isinstance(user, dict):
        user_id = user.get('id', user.get('username', user_name))
        username = user.get('username', user_name)
        role = user.get('role', 'viewer')
    else:
        try:
            user_id = str(user.id) if hasattr(user, 'id') else getattr(user, 'username', user_name)
            username = getattr(user, 'username', user_name)
            role = user.role.value if hasattr(user, 'role') else 'viewer'
        except Exception:
            user_id, username, role = user_name, user_name, 'viewer'
    # Compute effective permissions and store in session for downstream use
    try:
        custom_perms = resource_request_manager.get_user_custom_permissions(user_id)
        effective_permissions = enterprise_permissions.get_user_permissions(role, custom_perms)
        st.session_state.effective_permissions = effective_permissions
        st.session_state.current_user_id = user_id
        st.session_state.current_username = username
        st.session_state.current_role = role
    except Exception as _perm_err:
        st.session_state.effective_permissions = {}
    
    # Initialize MCP tracker with user info if not already done
    user_info = {
        "username": user_name,
        "email": user_email,
        "role": user.get('role', 'user') if user else 'user'
    }
    
    if mcp_tracker is None:
        try:
            mcp_tracker = MCPTracker(user_info)
            MCP_TRACKER_AVAILABLE = mcp_tracker.available
            if MCP_TRACKER_AVAILABLE:
                logger.info(f"MCP tracker initialized successfully for user: {user_name}")
            else:
                logger.warning("MCP tracker initialized but not available")
        except Exception as e:
            logger.error(f"Failed to initialize MCP tracker: {str(e)}")
            MCP_TRACKER_AVAILABLE = False
    
    # Display header
    st.markdown("### 🤖 Agent Assistant")
    st.markdown(f"**User:** {user_name} | **Email:** {user_email}")
    
    # Call the main agent assistant function
    agent_assistant_tab(available_indexes=available_indexes)

def load_agent_history():
    """Load the agent history from session state or initialize if not present"""
    if 'agent_history' not in st.session_state:
        st.session_state.agent_history = []
    
    return st.session_state.agent_history

def save_agent_history(history):
    """Save the updated agent history to session state"""
    st.session_state.agent_history = history

def run_controller_agent(prompt: str, index_name: str, agent_mode: str, response_tone: str) -> tuple[str, list]:
    """Run the controller agent and return the response and sources."""
    if not CONTROLLER_AGENT_AVAILABLE:
        return "The Controller Agent is currently unavailable. Please check the logs.", []

    try:
        # Check if this is a ByLaw query and modify index_name if needed
        if is_bylaw_query(prompt):
            logger.info(f"Detected ByLaw query in controller agent: {prompt}")
            # Prefer known bylaw indexes in order, but only if they exist
            preferred_candidates = [
                "ByLawS2_index",  # legacy name
                "ByLaw_index",
                "Bylaws_index",
                "Bylaws_New",
                "Bylaws-lanre",
            ]
            resolved = None
            # Try explicit candidates
            for cand in preferred_candidates:
                try:
                    if get_simple_index_path(cand):
                        resolved = cand
                        break
                except Exception:
                    continue
            # If still not found, scan available indexes for anything containing 'bylaw'
            if not resolved:
                try:
                    available = get_simple_indexes() or []
                    bylaw_like = [x for x in available if 'bylaw' in x.lower()]
                    if bylaw_like:
                        resolved = sorted(bylaw_like)[0]
                except Exception:
                    pass
            # Apply override only if we found a valid candidate
            if resolved:
                index_name = resolved
                logger.info(f"Overriding index to {index_name} for ByLaw query")
            else:
                logger.warning("No bylaw index found. Proceeding without override.")

        context = ModelContext(
            model_name="gpt-3.5-turbo",
            model_provider="OpenAI"  # Added missing model provider
        )
        context.parameters = {
            "temperature": 0.7,
            "max_tokens": 1500,
            "agent_mode": agent_mode,
            "response_tone": response_tone
        }

        with st.spinner("🤖 The agent is thinking..."):
            response_data = execute_controller_agent(
                user_prompt=prompt, 
                context=context, 
                index_name=index_name
            )

        if not response_data or "error" in response_data:
            error_msg = response_data.get('error', 'No response from agent.')
            st.error(f"Agent Error: {error_msg}")
            return f"An error occurred: {error_msg}", []

        result = response_data.get("result", "No response generated.")
        source_docs = response_data.get("source_documents", [])
        
        sources = []
        if source_docs:
            for doc in source_docs:
                if hasattr(doc, 'metadata') and 'source' in doc.metadata:
                    sources.append(os.path.basename(doc.metadata['source']))
        
        unique_sources = sorted(list(set(sources)))
        return result, unique_sources

    except Exception as e:
        logger.error(f"Error running controller agent: {e}\n{traceback.format_exc()}")
        return f"An error occurred while running the agent: {e}", []

def get_display_name(index_name: str) -> str:
    """Converts an index directory name to a user-friendly display name."""
    name = index_name.removesuffix("_index").replace("_", " ").title()
    return name

def agent_assistant_tab(available_indexes: List[str] = None):
    """Render the Agent Assistant tab"""
    global mcp_tracker, MCP_TRACKER_AVAILABLE
    
    # Create an MCP context for the overall tab session
    tab_context = None
    if MCP_TRACKER_AVAILABLE and mcp_tracker:
        tab_context = mcp_tracker.create_context(
            operation_type="AGENT_ASSISTANT_TAB",
            context_level=MCPContextLevel.BASIC
        )
        mcp_tracker.update_context(tab_context, {
            "session_start": time.time(),
            "tab_name": "Agent Assistant"
        })
    
    # Create columns for main content and sidebar
    main_col, sidebar_col = st.columns([3, 1])
    
    with sidebar_col:
        # Sidebar configuration
        st.subheader("🔧 Configuration")
        
        # Agent mode selector
        agent_mode = st.selectbox(
            "Agent Mode",
            ["Standard", "Advanced", "Expert"],
            index=0
        )
        
        # Response tone selector
        response_tone = st.selectbox(
            "Response Tone",
            ["Professional", "Casual", "Technical", "Creative", "Persuasive"],
            index=0
        )
        
        # Output format selector
        output_format = st.selectbox(
            "Output Format",
            ["Markdown", "HTML", "Plain Text", "JSON"],
            index=0
        )
        
        # Backend selection
        search_backend = render_backend_selector(key="agent_backend")
        
        # Document knowledge selection
        use_documents = st.checkbox("Use Document Knowledge", value=True, help="Enable document-based responses")
        # Define task mode based on document usage to avoid NameError later
        agent_task_mode = "Document-based Task" if use_documents else "General Task"
        
        if use_documents:
            if search_backend == "Weaviate (Cloud Vector DB)":
                # Weaviate collection selection
                selected_collection = render_collection_selector(
                    key="agent_collection",
                    label="Knowledge Base",
                    help_text="Choose a Weaviate collection for the agent"
                )
                
                if selected_collection:
                    index_name = selected_collection
                    st.success(f"✅ Using Weaviate: {selected_collection}")
                else:
                    st.warning("No Weaviate collections found. Please ingest documents first.")
                    index_name = None
            else:
                # FAISS index selection (fallback)
                if available_indexes:
                    # Create a mapping from display name to actual index name
                    index_display_map = {get_display_name(name): name for name in available_indexes}
                    display_names = sorted(list(index_display_map.keys()))
                    
                    selected_display_name = st.selectbox(
                        "Select Index",
                        options=display_names,
                        index=0,
                        help="Select the knowledge base for the agent to use."
                    )
                    # Get the actual index name from the selected display name
                    index_name = index_display_map.get(selected_display_name)
                else:
                    st.warning("No document indexes found. Please ingest documents first.")
                    index_name = None
        else:
            st.info("🤖 The agent will use its general knowledge to respond.")
            index_name = "General Knowledge"

        # Platform selector
        target_platform = st.selectbox(
            "Target Platform",
            ["General", "Microsoft Teams", "Slack", "Email", "Web", "Document"],
            index=0
        )

        st.divider()
        st.subheader("✉️ Email Delivery")
        # Determine latest response to prefill body
        latest_body = ""
        if 'agent_history' in st.session_state and st.session_state.agent_history:
            try:
                latest_body = st.session_state.agent_history[0].get('response', '') or ''
            except Exception:
                latest_body = ''

        use_latest = st.checkbox("Use latest response as email body", value=bool(latest_body))
        # Detect provider configuration from environment
        smtp_configured = bool(os.getenv("SMTP_HOST")) and bool(os.getenv("SMTP_USERNAME")) and bool(os.getenv("SMTP_PASSWORD"))
        graph_configured = bool(os.getenv("AZURE_TENANT_ID")) and bool(os.getenv("AZURE_CLIENT_ID")) and bool(os.getenv("AZURE_CLIENT_SECRET")) and bool(os.getenv("GRAPH_SENDER"))
        default_provider_index = 0 if smtp_configured else (1 if graph_configured else 0)
        st.caption(f"SMTP: {'Configured' if smtp_configured else 'Not configured'} | Graph: {'Configured' if graph_configured else 'Not configured'}")
        email_provider_label = st.selectbox(
            "Email Provider",
            ["SMTP", "Microsoft Graph (Outlook)"],
            index=default_provider_index,
            help="Choose how to send the email"
        )
        auto_fallback = st.checkbox(
            "Auto-fallback to configured provider",
            value=True,
            help="If the selected provider isn't configured, automatically fallback to the other provider if available."
        )
        # Provider configuration UI (session-based)
        with st.expander("Configure Email Providers (session)"):
            smtp_tab, graph_tab = st.tabs(["SMTP", "Microsoft Graph"])
            with smtp_tab:
                st.text("Set SMTP values for this session")
                smtp_host_in = st.text_input("SMTP Host", value=os.getenv("SMTP_HOST", ""), key="smtp_host_in")
                smtp_port_in = st.text_input("SMTP Port", value=os.getenv("SMTP_PORT", "587"), key="smtp_port_in")
                smtp_user_in = st.text_input("SMTP Username", value=os.getenv("SMTP_USERNAME", ""), key="smtp_user_in")
                smtp_pass_in = st.text_input("SMTP Password", type="password", value=os.getenv("SMTP_PASSWORD", ""), key="smtp_pass_in")
                smtp_from_in = st.text_input("SMTP From (optional)", value=os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", "")), key="smtp_from_in")
                smtp_tls_in = st.checkbox("Use TLS", value=(os.getenv("SMTP_USE_TLS", "true").lower() in ("1","true","yes","on")), key="smtp_tls_in")
                smtp_ssl_in = st.checkbox("Use SSL (implicit, port 465)", value=(os.getenv("SMTP_USE_SSL", "false").lower() in ("1","true","yes","on")), key="smtp_ssl_in")

                # Gmail helper hints (auto-detect by host or username domain)
                try:
                    host_lc = (smtp_host_in or "").strip().lower()
                    user_lc = (smtp_user_in or "").strip().lower()
                    from_lc = (smtp_from_in or "").strip().lower()
                    domain_hint = (user_lc.split("@", 1)[1] if "@" in user_lc else "") or (from_lc.split("@", 1)[1] if "@" in from_lc else "")
                    is_gmail = (
                        host_lc in ("smtp.gmail.com", "smtp.googlemail.com")
                        or domain_hint in ("gmail.com", "googlemail.com")
                    )
                except Exception:
                    is_gmail = False

                if is_gmail:
                    st.info(
                        "Using Gmail? If 2‑Step Verification is enabled, you must use an App Password for SMTP.\n\n"
                        "Steps:\n"
                        "1) Enable 2‑Step Verification\n"
                        "2) Create an App Password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)\n"
                        "3) Use the 16‑char App Password here (not your normal password)\n\n"
                        "If you get blocked, try: [DisplayUnlockCaptcha](https://accounts.google.com/DisplayUnlockCaptcha)",
                    )
                    cols_gmail = st.columns(2)
                    with cols_gmail[0]:
                        if st.button("Fill Gmail defaults", key="btn_fill_gmail_defaults"):
                            try:
                                st.session_state.smtp_host_in = "smtp.gmail.com"
                                st.session_state.smtp_port_in = "587"
                                st.session_state.smtp_tls_in = True
                                st.success("Filled Gmail defaults (host, port, TLS).")
                                st.rerun()
                            except Exception:
                                pass
                    with cols_gmail[1]:
                        st.markdown("[Create App Password →](https://myaccount.google.com/apppasswords)")
                if st.button("Save SMTP (session)", key="save_smtp_session"):
                    os.environ["SMTP_HOST"] = smtp_host_in
                    os.environ["SMTP_PORT"] = smtp_port_in or "587"
                    os.environ["SMTP_USERNAME"] = smtp_user_in
                    os.environ["SMTP_PASSWORD"] = smtp_pass_in
                    os.environ["SMTP_FROM"] = smtp_from_in or smtp_user_in
                    os.environ["SMTP_USE_TLS"] = "true" if smtp_tls_in else "false"
                    os.environ["SMTP_USE_SSL"] = "true" if smtp_ssl_in else "false"
                    st.success("SMTP settings saved for this session.")
                    st.rerun()
                if st.button("Save SMTP (.env.local)", key="save_smtp_envfile"):
                    path = write_env_local({
                        "SMTP_HOST": smtp_host_in,
                        "SMTP_PORT": smtp_port_in or "587",
                        "SMTP_USERNAME": smtp_user_in,
                        "SMTP_PASSWORD": smtp_pass_in,
                        "SMTP_FROM": smtp_from_in or smtp_user_in,
                        "SMTP_USE_TLS": "true" if smtp_tls_in else "false",
                        "SMTP_USE_SSL": "true" if smtp_ssl_in else "false",
                    }, section="SMTP Settings")
                    st.success(f"Saved to {path}")
                    load_env_files()
                    st.rerun()
            with graph_tab:
                st.text("Set Microsoft Graph values for this session")
                tenant_in = st.text_input("Azure Tenant ID", value=os.getenv("AZURE_TENANT_ID", ""), key="tenant_in")
                client_id_in = st.text_input("Azure Client ID", value=os.getenv("AZURE_CLIENT_ID", ""), key="client_id_in")
                client_secret_in = st.text_input("Azure Client Secret", type="password", value=os.getenv("AZURE_CLIENT_SECRET", ""), key="client_secret_in")
                sender_in = st.text_input("Graph Sender (UPN or User ID)", value=os.getenv("GRAPH_SENDER", ""), key="sender_in")
                scope_in = st.text_input("Graph Scope (optional)", value=os.getenv("GRAPH_SCOPE", "https://graph.microsoft.com/.default"), key="scope_in")
                if st.button("Save Graph (session)", key="save_graph_session"):
                    os.environ["AZURE_TENANT_ID"] = tenant_in
                    os.environ["AZURE_CLIENT_ID"] = client_id_in
                    os.environ["AZURE_CLIENT_SECRET"] = client_secret_in
                    os.environ["GRAPH_SENDER"] = sender_in
                    os.environ["GRAPH_SCOPE"] = scope_in or "https://graph.microsoft.com/.default"
                    st.success("Microsoft Graph settings saved for this session.")
                    st.rerun()
                if st.button("Save Graph (.env.local)", key="save_graph_envfile"):
                    path = write_env_local({
                        "AZURE_TENANT_ID": tenant_in,
                        "AZURE_CLIENT_ID": client_id_in,
                        "AZURE_CLIENT_SECRET": client_secret_in,
                        "GRAPH_SENDER": sender_in,
                        "GRAPH_SCOPE": scope_in or "https://graph.microsoft.com/.default",
                    }, section="Microsoft Graph Settings")
                    st.success(f"Saved to {path}")
                    load_env_files()
                    st.rerun()

        recipients_input = st.text_input("Recipients (comma-separated)", value="", help="e.g. user1@company.com, user2@company.com")
        email_subject = st.text_input("Subject", value="Agent Output")
        subtype_choice = st.selectbox("Email body format", ["Plain text", "HTML"], index=0)
        subtype_value = "plain" if subtype_choice == "Plain text" else "html"
        email_body = st.text_area("Body", value=(latest_body if use_latest else ""), height=120)
        # Attachments
        attachments_files = st.file_uploader("Attachments (optional)", accept_multiple_files=True)
        attachments_list = []
        if attachments_files:
            for f in attachments_files:
                try:
                    data = f.getvalue()
                    content_b64 = base64.b64encode(data).decode("utf-8")
                    mime_type, _ = mimetypes.guess_type(f.name)
                    attachments_list.append({
                        "filename": f.name,
                        "mime_type": mime_type or "application/octet-stream",
                        "content": content_b64
                    })
                except Exception:
                    pass

        # Permission gate for Email Sending feature
        perms = st.session_state.get('effective_permissions', {})
        can_send_email = enterprise_permissions.can_access_feature(perms, 'email_sending', PermissionLevel.WRITE)
        if not can_send_email:
            st.warning("You don't have permission to send emails. Please request access below.")
            with st.expander("Request access to Email Sending"):
                justification = st.text_area("Business Justification", key="just_email", placeholder="Explain why you need Email Sending access...")
                if st.button("Request Email Access", key="btn_req_email"):
                    uid = st.session_state.get('current_user_id', 'unknown')
                    uname = st.session_state.get('current_username', 'unknown')
                    try:
                        req_id = resource_request_manager.create_request(uid, uname, 'email_sending', PermissionLevel.WRITE, justification or "Requested via Agent tab")
                        st.success(f"Request submitted. ID: {req_id}")
                    except Exception as e:
                        st.error(f"Failed to submit request: {e}")
        if can_send_email and st.button("Send Email now", use_container_width=True, key="send_email_now"):
            if not recipients_input.strip():
                st.warning("Please enter at least one recipient email address.")
            else:
                try:
                    provider_key = 'smtp' if email_provider_label.startswith('SMTP') else 'ms_graph'
                    # Prevent sending if selected provider is not configured
                    can_send = True
                    if provider_key == 'smtp' and not smtp_configured:
                        if auto_fallback and graph_configured:
                            st.info("Selected provider SMTP not configured. Falling back to Microsoft Graph.")
                            provider_key = 'ms_graph'
                        else:
                            st.error("SMTP not configured. Set SMTP_HOST/PORT/USERNAME/PASSWORD (and optional SMTP_USE_TLS/SMTP_FROM), or select Microsoft Graph.")
                            can_send = False
                    elif provider_key == 'ms_graph' and not graph_configured:
                        if auto_fallback and smtp_configured:
                            st.info("Selected provider Microsoft Graph not configured. Falling back to SMTP.")
                            provider_key = 'smtp'
                        else:
                            st.error("Microsoft Graph not configured. Set AZURE_TENANT_ID/AZURE_CLIENT_ID/AZURE_CLIENT_SECRET/GRAPH_SENDER, or select SMTP.")
                            can_send = False
                    
                    if not can_send:
                        # Skip sending
                        raise Exception("Email provider not configured")
                    args = {
                        "recipients": recipients_input,
                        "subject": email_subject,
                        "body": email_body,
                        "provider": provider_key,
                        "subtype": subtype_value,
                    }
                    if attachments_list:
                        try:
                            args["attachments_json"] = json.dumps(attachments_list)
                        except Exception:
                            pass
                    # Execute tool via FunctionHandler
                    result = FunctionHandler.execute("send_email", args)
                    status = (result or {}).get("status", "unknown")
                    if status == "sent":
                        st.success(f"Email sent via {result.get('provider', provider_key)}")
                    else:
                        st.error(f"Failed to send email: {(result or {}).get('error', 'Unknown error')}")

                    # MCP logging
                    if MCP_TRACKER_AVAILABLE and mcp_tracker:
                        try:
                            send_ctx = mcp_tracker.create_context("SEND_EMAIL", MCPContextLevel.BASIC)
                            mcp_tracker.update_context(send_ctx, {
                                "provider": provider_key,
                                "recipients_count": len([r for r in recipients_input.split(',') if r.strip()]),
                                "status": status
                            })
                            mcp_tracker.log_operation(
                                context=send_ctx,
                                operation="SEND_EMAIL",
                                status=status,
                                details={"provider": provider_key}
                            )
                        except Exception:
                            pass
                except Exception as e:
                    st.error(f"Error sending email: {e}")

        # Quick test configuration buttons
        test_to = st.text_input("Test recipient (optional)", value="", help="Enter an email address to send test messages")
        col_test1, col_test2 = st.columns(2)
        with col_test1:
            if st.button("Send SMTP Test", key="send_test_smtp", disabled=not smtp_configured):
                try:
                    if not test_to.strip():
                        st.warning("Enter a test recipient email address.")
                    else:
                        args = {
                            "recipients": test_to,
                            "subject": "VaultMind SMTP Test",
                            "body": f"This is an SMTP test sent at {datetime.now().isoformat()}.",
                            "provider": "smtp",
                            "subtype": "plain",
                        }
                        result = FunctionHandler.execute("send_email", args)
                        status = (result or {}).get("status", "unknown")
                        if status == "sent":
                            st.success("SMTP test email sent")
                        else:
                            st.error(f"SMTP test failed: {(result or {}).get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error sending SMTP test: {e}")
        with col_test2:
            if st.button("Send Graph Test", key="send_test_graph", disabled=not graph_configured):
                try:
                    if not test_to.strip():
                        st.warning("Enter a test recipient email address.")
                    else:
                        args = {
                            "recipients": test_to,
                            "subject": "VaultMind Graph Test",
                            "body": f"This is a Microsoft Graph test sent at {datetime.now().isoformat()}.",
                            "provider": "ms_graph",
                            "subtype": "plain",
                        }
                        result = FunctionHandler.execute("send_email", args)
                        status = (result or {}).get("status", "unknown")
                        if status == "sent":
                            st.success("Microsoft Graph test email sent")
                        else:
                            st.error(f"Graph test failed: {(result or {}).get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error sending Graph test: {e}")

        # Provider-specific send buttons
        st.caption("Or send directly with a specific provider:")
        col_send1, col_send2 = st.columns(2)
        with col_send1:
            if can_send_email and st.button("Send via SMTP", key="send_email_smtp", use_container_width=True, disabled=not smtp_configured):
                if not recipients_input.strip():
                    st.warning("Please enter at least one recipient email address.")
                else:
                    try:
                        args = {
                            "recipients": recipients_input,
                            "subject": email_subject,
                            "body": email_body,
                            "provider": "smtp",
                            "subtype": subtype_value,
                        }
                        if attachments_list:
                            try:
                                args["attachments_json"] = json.dumps(attachments_list)
                            except Exception:
                                pass
                        result = FunctionHandler.execute("send_email", args)
                        status = (result or {}).get("status", "unknown")
                        if status == "sent":
                            st.success("Email sent via SMTP")
                        else:
                            st.error(f"SMTP send failed: {(result or {}).get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error sending via SMTP: {e}")
        with col_send2:
            if can_send_email and st.button("Send via Graph", key="send_email_graph_btn", use_container_width=True, disabled=not graph_configured):
                if not recipients_input.strip():
                    st.warning("Please enter at least one recipient email address.")
                else:
                    try:
                        args = {
                            "recipients": recipients_input,
                            "subject": email_subject,
                            "body": email_body,
                            "provider": "ms_graph",
                            "subtype": subtype_value,
                        }
                        if attachments_list:
                            try:
                                args["attachments_json"] = json.dumps(attachments_list)
                            except Exception:
                                pass
                        result = FunctionHandler.execute("send_email", args)
                        status = (result or {}).get("status", "unknown")
                        if status == "sent":
                            st.success("Email sent via Microsoft Graph")
                        else:
                            st.error(f"Graph send failed: {(result or {}).get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error sending via Microsoft Graph: {e}")

        st.divider()
        st.subheader("💬 Slack / Teams Messaging")
        perms = st.session_state.get('effective_permissions', {})
        can_slack = enterprise_permissions.can_access_feature(perms, 'slack_messaging', PermissionLevel.WRITE)
        can_teams = enterprise_permissions.can_access_feature(perms, 'teams_messaging', PermissionLevel.WRITE)
        slack_configured = bool(os.getenv("SLACK_WEBHOOK_URL"))
        teams_configured = bool(os.getenv("TEAMS_WEBHOOK_URL"))
        st.caption(f"Slack: {'Configured' if slack_configured else 'Not configured'} | Teams: {'Configured' if teams_configured else 'Not configured'}")

        with st.expander("Configure Slack/Teams (session)"):
            st.text("Set Slack/Teams webhook URLs for this session or persist to .env.local")
            slack_webhook_in = st.text_input("Slack Webhook URL", value=os.getenv("SLACK_WEBHOOK_URL", ""), key="slack_webhook_in")
            teams_webhook_in = st.text_input("Teams Webhook URL", value=os.getenv("TEAMS_WEBHOOK_URL", ""), key="teams_webhook_in")
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                if st.button("Save Slack (session)", key="save_slack_session"):
                    os.environ["SLACK_WEBHOOK_URL"] = slack_webhook_in
                    st.success("Slack webhook saved for this session.")
                    st.rerun()
                if st.button("Save Teams (session)", key="save_teams_session"):
                    os.environ["TEAMS_WEBHOOK_URL"] = teams_webhook_in
                    st.success("Teams webhook saved for this session.")
                    st.rerun()
            with col_cfg2:
                if st.button("Save Slack (.env.local)", key="save_slack_envfile"):
                    path = write_env_local({"SLACK_WEBHOOK_URL": slack_webhook_in}, section="Slack Settings")
                    st.success(f"Saved to {path}")
                    load_env_files()
                    st.rerun()
                if st.button("Save Teams (.env.local)", key="save_teams_envfile"):
                    path = write_env_local({"TEAMS_WEBHOOK_URL": teams_webhook_in}, section="Teams Settings")
                    st.success(f"Saved to {path}")
                    load_env_files()
                    st.rerun()

        # Slack request gate
        if not can_slack:
            st.info("You don't have permission to send Slack messages. Request access below.")
            with st.expander("Request Slack Messaging Access"):
                just_slack = st.text_area("Business Justification", key="just_slack", placeholder="Why do you need Slack messaging?")
                if st.button("Request Slack Access", key="btn_req_slack"):
                    uid = st.session_state.get('current_user_id', 'unknown')
                    uname = st.session_state.get('current_username', 'unknown')
                    try:
                        req_id = resource_request_manager.create_request(uid, uname, 'slack_messaging', PermissionLevel.WRITE, just_slack or "Requested via Agent tab")
                        st.success(f"Request submitted. ID: {req_id}")
                    except Exception as e:
                        st.error(f"Failed to submit request: {e}")
        # Teams request gate
        if not can_teams:
            st.info("You don't have permission to send Teams messages. Request access below.")
            with st.expander("Request Teams Messaging Access"):
                just_teams = st.text_area("Business Justification", key="just_teams", placeholder="Why do you need Teams messaging?")
                if st.button("Request Teams Access", key="btn_req_teams"):
                    uid = st.session_state.get('current_user_id', 'unknown')
                    uname = st.session_state.get('current_username', 'unknown')
                    try:
                        req_id = resource_request_manager.create_request(uid, uname, 'teams_messaging', PermissionLevel.WRITE, just_teams or "Requested via Agent tab")
                        st.success(f"Request submitted. ID: {req_id}")
                    except Exception as e:
                        st.error(f"Failed to submit request: {e}")

        if can_slack or can_teams:
            use_latest_msg = st.checkbox("Use latest response as message", value=bool(latest_body), key="use_latest_msg")
            message_text = st.text_area("Message", value=(latest_body if use_latest_msg else ""), height=100, key="msg_text")
            col_msg1, col_msg2 = st.columns(2)
            with col_msg1:
                if can_slack and st.button("Send to Slack", key="send_to_slack", use_container_width=True):
                    if not slack_configured:
                        st.error("Slack webhook not configured. Configure above or set SLACK_WEBHOOK_URL.")
                    elif not message_text.strip():
                        st.warning("Enter a message to send.")
                    else:
                        res = FunctionHandler.execute("send_slack_message", {
                            "message": message_text,
                        })
                        if (res or {}).get("status") == "sent":
                            st.success("Sent to Slack")
                        else:
                            st.error(f"Slack send failed: {(res or {}).get('error', 'Unknown error')}")
                        if MCP_TRACKER_AVAILABLE and mcp_tracker:
                            try:
                                ctx = mcp_tracker.create_context("SEND_SLACK", MCPContextLevel.BASIC)
                                mcp_tracker.log_operation(context=ctx, operation="SEND_SLACK", status=(res or {}).get("status", "unknown"))
                            except Exception:
                                pass
            with col_msg2:
                teams_title = st.text_input("Teams Title (optional)", value="", key="teams_title")
                if can_teams and st.button("Send to Teams", key="send_to_teams", use_container_width=True):
                    if not teams_configured:
                        st.error("Teams webhook not configured. Configure above or set TEAMS_WEBHOOK_URL.")
                    elif not message_text.strip():
                        st.warning("Enter a message to send.")
                    else:
                        res = FunctionHandler.execute("send_teams_message", {
                            "message": message_text,
                            "title": teams_title or None,
                        })
                        if (res or {}).get("status") == "sent":
                            st.success("Sent to Teams")
                        else:
                            st.error(f"Teams send failed: {(res or {}).get('error', 'Unknown error')}")
                        if MCP_TRACKER_AVAILABLE and mcp_tracker:
                            try:
                                ctx = mcp_tracker.create_context("SEND_TEAMS", MCPContextLevel.BASIC)
                                mcp_tracker.log_operation(context=ctx, operation="SEND_TEAMS", status=(res or {}).get("status", "unknown"))
                            except Exception:
                                pass

    # Main content column
    with main_col:
        # Category selection
        st.subheader("Select Category")
        
        # Define categories with icons
        categories = {
            "Document Operations": "📄",
            "Communication": "💬",
            "Analysis & Research": "🔍",
            "Creative": "🎨",
            "Code & Technical": "💻",
            "Business": "📊"
        }
        
        # Define tasks for each category
        category_tasks = {
            "Document Operations": ["Document Summary", "Document Improvement", "Content Creation", "Format Conversion"],
            "Communication": ["Email Draft", "Teams/Slack Message", "Meeting Summary", "Announcement"],
            "Analysis & Research": ["Research Topic", "Problem Analysis", "Data Analysis", "Comparative Study"],
            "Creative": ["Creative Writing", "Brainstorming", "Content Creation", "Visual Concept"],
            "Code & Technical": ["Code Review", "Documentation", "Debugging Help", "API Design"],
            "Business": ["Business Proposal", "Strategic Plan", "Financial Analysis", "Marketing Plan"]
        }
        
        # Create category buttons in 3 columns
        col1, col2, col3 = st.columns(3)
        columns = [col1, col2, col3]
        
        selected_category = None
        
        for i, (category, icon) in enumerate(categories.items()):
            col_idx = i % 3
            with columns[col_idx]:
                if st.button(f"{icon} {category}", key=f"cat_{category}", use_container_width=True):
                    selected_category = category
        
        # Store selected category in session state
        if selected_category:
            st.session_state.agent_category = selected_category
        
        if 'agent_category' in st.session_state:
            selected_category = st.session_state.agent_category
            st.markdown(f"### Selected: {categories.get(selected_category, '')} {selected_category}")
            
            # Now show operation options for the selected category
            st.subheader("Select Operation")
            
            operations = category_tasks.get(selected_category, [])
            
            # Display operations as buttons in 2 columns
            col1, col2 = st.columns(2)
            cols = [col1, col2]
            
            selected_operation = None
            
            for i, operation in enumerate(operations):
                col_idx = i % 2
                with cols[col_idx]:
                    if st.button(operation, key=f"op_{operation}", use_container_width=True):
                        selected_operation = operation
            
            # Store selected operation in session state
            if selected_operation:
                st.session_state.agent_operation = selected_operation
        
        # Display the task input form if an operation is selected
        if 'agent_category' in st.session_state and 'agent_operation' in st.session_state:
            st.subheader("Task Details")
            
            # Display the current selections
            st.info(f"**Category:** {st.session_state.agent_category} | **Operation:** {st.session_state.agent_operation} | **Mode:** {agent_mode}")
            
            task_prompts = {
                "Document Summary": "Enter the document content or describe what to summarize...",
                "Document Improvement": "Enter the document to improve or describe the improvement needed...",
                "Research Topic": "Describe the research topic or question...",
                "Data Analysis": "Describe the data and analysis you need...",
                "Email Draft": "Describe the email you want to draft...",
                "Creative Writing": "Describe the creative content you want to generate...",
                "Business Proposal": "Describe the business proposal you need...",
                "Problem Analysis": "Describe the problem that needs analysis..."
            }
            
            current_operation = st.session_state.agent_operation
            task_prompt = task_prompts.get(current_operation, "Describe your task in detail...")
            
            task_description = st.text_area("Task Description", height=100, placeholder=task_prompt, key="latest_task_description")

            submit_col1, submit_col2 = st.columns([3, 1])
            with submit_col2:
                if st.button("Run Agent 🚀", type="primary", use_container_width=True):
                    if task_description:
                        with st.spinner("Agent is processing your request..."):
                            current_index_name = index_name
                            if agent_task_mode == "Document-based Task":
                                if not current_index_name:
                                    st.error("Please select an index for document-based tasks.")
                                    st.stop()
                            else: 
                                current_index_name = "General Knowledge"

                            if CONTROLLER_AGENT_AVAILABLE:
                                response_content, sources = run_controller_agent(
                                    prompt=task_description,
                                    index_name=current_index_name,
                                    agent_mode=agent_mode,
                                    response_tone=response_tone
                                )
                            else:
                                response_content = "Error: The Agent Controller is not available. Please check the system logs."
                                sources = []

                            history = load_agent_history()
                            history.insert(0, {
                                "id": str(uuid.uuid4()),  # Add unique ID for each history item
                                "category": st.session_state.agent_category,
                                "operation": st.session_state.agent_operation,
                                "task": task_description,
                                "response": response_content,
                                "sources": sources,
                                "timestamp": datetime.now().isoformat(),
                                "config": {
                                    "mode": agent_mode,
                                    "tone": response_tone,
                                    "format": output_format,
                                    "platform": target_platform,
                                    "task_mode": agent_task_mode,
                                    "index": current_index_name if agent_task_mode == "Document-based Task" else "N/A"
                                }
                            })
                            save_agent_history(history[:Config.MAX_HISTORY_ITEMS])
                            st.rerun()
                    else:
                        st.warning("Please enter a task description.")

    # Display agent response history
    st.subheader("📜 Agent Task History")
    history = load_agent_history()

    if not history:
        st.info("No tasks have been run yet. Submit a task above to see the results here.")
    else:
        for i, item in enumerate(history):
            with st.expander(f"**{item['timestamp']}**: {item['task'][:50]}...", expanded=(i == 0)):
                st.markdown(f"**Task:** {item['task']}")
                st.markdown("**Response:**")
                st.markdown(item['response'], unsafe_allow_html=True)
                if item.get('sources'):
                    st.markdown("**Sources:**")
                    for source in item['sources']:
                        st.markdown(f"- `{source}`")
                
                # Display configuration for the task
                st.markdown("---_Configuration_---")
                config = item.get('config', {})
                cols = st.columns(3)
                cols[0].metric("Task Mode", config.get('task_mode', 'N/A'))
                cols[1].metric("Agent Mode", config.get('mode', 'N/A'))
                cols[2].metric("Index Used", config.get('index', 'N/A'))

                # Add reuse and delete buttons
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(f"Reuse Task", key=f"reuse_{item['id']}"):
                        st.session_state.latest_task_description = item['task']
                        st.rerun()
                with col2:
                    if st.button(f"Delete Task", key=f"delete_{item['id']}"):
                        st.session_state.agent_history = [h for h in st.session_state.agent_history if h['id'] != item['id']]
                        save_agent_history(st.session_state.agent_history)
                        st.rerun()

def retrieve_documents(query: str, index_name: str) -> List[Dict]:
    """
    Updated to use central Weaviate instance
    Returns documents with additional agent-specific metadata
    """
    try:
        from utils.weaviate_manager import get_weaviate_manager
        wm = get_weaviate_manager()
        
        # Get documents with agent-specific filters
        results = wm.get_documents_for_tab(
            collection_name=index_name,
            tab_name="agent_assistant",
            query=query,
            limit=10
        )
        
        # Add agent-specific processing
        for doc in results:
            doc['agent_metadata'] = {
                'retrieval_time': datetime.now().isoformat(),
                'processed': False
            }
            
        return results
        
    except Exception as e:
        logger.error(f"Weaviate retrieval failed: {e}")
        return []
