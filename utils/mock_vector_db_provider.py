"""
This module creates a mock vector database provider that doesn't require the faiss library.
It provides the same interface as the real vector database provider but returns mock data.
"""

import os
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockSearchResult:
    """Mock search result class"""
    def __init__(self, content: str, source: str, relevance: float = 0.0):
        self.content = content
        self.source = source
        self.relevance = relevance
        self.metadata = {"source": source, "score": relevance}

class MockVectorDBProvider:
    """
    Mock vector database provider for testing and development
    when the real vector database is not available
    """
    
    def __init__(self):
        """Initialize the mock vector database provider"""
        # Use the actual indexes found in the system
        self.available_indexes = self._discover_real_indexes()
        self.last_refresh = datetime.now()
        self.mock_data = {
            "cloud security": [
                MockSearchResult(
                    content="Cloud security is a fundamental consideration for enterprise deployments. AWS provides comprehensive security features including IAM for access control, encryption at rest and in transit, and network security.",
                    source="AWS Security Documentation",
                    relevance=0.95
                ),
                MockSearchResult(
                    content="Best practices for cloud security include implementing the principle of least privilege, regular security assessments, and encryption of sensitive data.",
                    source="Cloud Security Guide",
                    relevance=0.87
                ),
                MockSearchResult(
                    content="AWS Shield provides DDoS protection for applications running on AWS, helping to ensure availability during attacks.",
                    source="AWS Shield Documentation",
                    relevance=0.79
                )
            ],
            "default": [
                MockSearchResult(
                    content="This is a mock search result from the vector database. The real database is not available.",
                    source="Mock Vector DB",
                    relevance=0.75
                ),
                MockSearchResult(
                    content="To use the real vector database, install faiss-cpu and sentence-transformers packages.",
                    source="Mock Vector DB",
                    relevance=0.70
                )
            ]
        }
    
    def _discover_real_indexes(self) -> List[str]:
        """Discover actual indexes in the system"""
        indexes = []
        
        # Check data/faiss_index directory
        faiss_dir = Path("data/faiss_index")
        if faiss_dir.exists():
            # Check for direct index files
            if (faiss_dir / "index.faiss").exists():
                indexes.append("default_faiss")
            
            # Check subdirectories
            for item in faiss_dir.iterdir():
                if item.is_dir():
                    indexes.append(item.name)
        
        # Check data/indexes directory
        indexes_dir = Path("data/indexes")
        if indexes_dir.exists():
            for item in indexes_dir.iterdir():
                if item.is_dir():
                    indexes.append(item.name)
        
        # If no indexes found, provide fallback
        if not indexes:
            indexes = ["enterprise_docs", "aws_docs", "general_knowledge"]
        
        logger.info(f"Discovered real indexes: {indexes}")
        return indexes
    
    def search(self, query: str, max_results: int = 5) -> List[MockSearchResult]:
        """
        Search the mock vector database
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of MockSearchResult objects
        """
        logger.info(f"Mock search for: {query}")
        
        # Check if we have mock data for this query
        for key in self.mock_data:
            if key.lower() in query.lower():
                return self.mock_data[key][:max_results]
        
        # Return default mock data
        return self.mock_data["default"][:max_results]
    
    def search_index(self, query: str, index_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search a specific index in the mock vector database
        
        Args:
            query: The search query
            index_name: Name of the index to search
            top_k: Maximum number of results to return
            
        Returns:
            List of search results as dictionaries
        """
        results = self.search(query, top_k)
        return [{"content": r.content, "metadata": {"source": r.source}} for r in results]
    
    def get_available_indexes(self, force_refresh: bool = False) -> List[str]:
        """
        Get all available vector indexes
        
        Args:
            force_refresh: If True, force a refresh of the available indexes
            
        Returns:
            List of available index names
        """
        return self.available_indexes
    
    def get_vector_db_status(self) -> Tuple[str, str]:
        """
        Get the current status of vector database connections
        
        Returns:
            Tuple of (status, message) where status is "Ready" or "Error"
        """
        index_count = len(self.available_indexes)
        return ("Ready", f"{index_count} Index(es) Available")
    
    def find_index_path(self, index_name: str) -> Optional[Path]:
        """
        Find the path to a vector index
        
        Args:
            index_name: Name of the index
            
        Returns:
            Path to the index or None if not found
        """
        if index_name in self.available_indexes:
            return Path("mock_path") / index_name
        return None

# Singleton instance
_mock_provider_instance = None

def get_mock_vector_db_provider() -> MockVectorDBProvider:
    """Get the singleton MockVectorDBProvider instance"""
    global _mock_provider_instance
    
    if _mock_provider_instance is None:
        _mock_provider_instance = MockVectorDBProvider()
        logger.info("Created mock vector database provider")
    
    return _mock_provider_instance
