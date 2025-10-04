"""
Enhanced Metadata Search
=======================

This module provides advanced metadata search capabilities for the VaultMIND Knowledge Assistant.
It allows filtering documents based on metadata fields like file type, date, size, and custom tags.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union, Set
from pathlib import Path
import json
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import the document metadata manager
try:
    from utils.enhanced_document_processor import DocumentMetadata, DEFAULT_METADATA_PATH
    metadata_manager = DocumentMetadata()
    METADATA_AVAILABLE = True
except ImportError:
    logger.warning("Document metadata manager not available.")
    METADATA_AVAILABLE = False
    metadata_manager = None

class MetadataSearchEngine:
    """
    Advanced metadata search engine for filtering documents based on metadata
    """
    
    def __init__(self, metadata_path: Optional[str] = None):
        """
        Initialize the metadata search engine
        
        Args:
            metadata_path: Path to the metadata store
        """
        self.metadata_path = metadata_path or DEFAULT_METADATA_PATH if 'DEFAULT_METADATA_PATH' in globals() else "data/document_metadata.json"
        self.metadata = {}
        self._load_metadata()
        
    def _load_metadata(self):
        """Load document metadata from disk"""
        if not METADATA_AVAILABLE:
            logger.warning("Metadata manager not available, using basic metadata search")
            try:
                metadata_path = Path(self.metadata_path)
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        self.metadata = json.load(f)
                    logger.info(f"Loaded metadata for {len(self.metadata)} documents")
                else:
                    logger.warning(f"Metadata file not found: {metadata_path}")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        else:
            # Use the metadata manager
            self.metadata = metadata_manager.get_all_metadata()
            logger.info(f"Loaded metadata for {len(self.metadata)} documents using metadata manager")
            
    def refresh_metadata(self):
        """Refresh metadata from disk"""
        self._load_metadata()
        
    def search_by_file_type(self, file_types: List[str]) -> List[str]:
        """
        Search for documents by file type
        
        Args:
            file_types: List of file extensions (without dot, e.g. 'pdf', 'docx')
            
        Returns:
            List of document IDs matching the file types
        """
        results = []
        for doc_id, doc_metadata in self.metadata.items():
            file_extension = doc_metadata.get("file_extension", "").lower().lstrip(".")
            if file_extension in file_types:
                results.append(doc_id)
        return results
        
    def search_by_date_range(self, start_date: str, end_date: str, date_field: str = "processing_date") -> List[str]:
        """
        Search for documents by date range
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            date_field: Metadata field to check (processing_date, file_created, file_modified)
            
        Returns:
            List of document IDs with dates in the specified range
        """
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
        except ValueError:
            logger.error(f"Invalid date format. Use ISO format (YYYY-MM-DD)")
            return []
            
        results = []
        for doc_id, doc_metadata in self.metadata.items():
            if date_field in doc_metadata:
                try:
                    # Parse the date, handling different formats
                    doc_date_str = doc_metadata[date_field]
                    # If only the date part is needed (without time)
                    if "T" in doc_date_str:
                        doc_date_str = doc_date_str.split("T")[0]
                    
                    doc_date = datetime.fromisoformat(doc_date_str)
                    if start <= doc_date <= end:
                        results.append(doc_id)
                except (ValueError, TypeError):
                    # Skip documents with invalid date format
                    continue
        
        return results
        
    def search_by_size_range(self, min_size_mb: float, max_size_mb: float) -> List[str]:
        """
        Search for documents by file size range
        
        Args:
            min_size_mb: Minimum file size in MB
            max_size_mb: Maximum file size in MB
            
        Returns:
            List of document IDs with size in the specified range
        """
        results = []
        for doc_id, doc_metadata in self.metadata.items():
            file_size_mb = doc_metadata.get("file_size_mb", 0)
            if min_size_mb <= file_size_mb <= max_size_mb:
                results.append(doc_id)
        return results
        
    def search_by_custom_field(self, field_name: str, field_value: Any) -> List[str]:
        """
        Search for documents by a custom metadata field
        
        Args:
            field_name: Name of the metadata field
            field_value: Value to match
            
        Returns:
            List of document IDs with matching field value
        """
        results = []
        for doc_id, doc_metadata in self.metadata.items():
            if field_name in doc_metadata and doc_metadata[field_name] == field_value:
                results.append(doc_id)
        return results
        
    def search_by_text_in_metadata(self, search_text: str) -> List[str]:
        """
        Search for documents with metadata containing the search text
        
        Args:
            search_text: Text to search for in metadata
            
        Returns:
            List of document IDs with metadata containing the search text
        """
        results = []
        search_text_lower = search_text.lower()
        
        for doc_id, doc_metadata in self.metadata.items():
            # Convert metadata to string and search
            metadata_str = json.dumps(doc_metadata).lower()
            if search_text_lower in metadata_str:
                results.append(doc_id)
                
        return results
        
    def combine_search_results(self, result_sets: List[List[str]], operation: str = "and") -> List[str]:
        """
        Combine multiple search result sets
        
        Args:
            result_sets: List of result sets (each a list of document IDs)
            operation: How to combine the results ("and" or "or")
            
        Returns:
            Combined list of document IDs
        """
        if not result_sets:
            return []
            
        if len(result_sets) == 1:
            return result_sets[0]
            
        if operation.lower() == "and":
            # Intersection of all sets
            result = set(result_sets[0])
            for result_set in result_sets[1:]:
                result.intersection_update(set(result_set))
            return list(result)
        else:  # "or"
            # Union of all sets
            result = set()
            for result_set in result_sets:
                result.update(set(result_set))
            return list(result)
            
    def get_metadata_for_documents(self, doc_ids: List[str]) -> Dict[str, Dict]:
        """
        Get metadata for a list of document IDs
        
        Args:
            doc_ids: List of document IDs
            
        Returns:
            Dictionary mapping document IDs to their metadata
        """
        result = {}
        for doc_id in doc_ids:
            if doc_id in self.metadata:
                result[doc_id] = self.metadata[doc_id]
        return result
        
    def parse_metadata_query(self, query: str) -> Dict[str, Any]:
        """
        Parse a metadata query string into search parameters
        
        Format examples:
        - type:pdf                  (file type)
        - date:2023-01-01..2023-12-31  (date range)
        - size:1..10                (size range in MB)
        - author:John               (custom field)
        
        Args:
            query: Metadata query string
            
        Returns:
            Dictionary with parsed search parameters
        """
        params = {}
        
        # File type pattern
        type_pattern = r'type:([a-zA-Z0-9,]+)'
        type_match = re.search(type_pattern, query)
        if type_match:
            file_types = type_match.group(1).split(',')
            params['file_types'] = file_types
            
        # Date range pattern
        date_pattern = r'date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})'
        date_match = re.search(date_pattern, query)
        if date_match:
            params['start_date'] = date_match.group(1)
            params['end_date'] = date_match.group(2)
            
        # Size range pattern
        size_pattern = r'size:(\d+(?:\.\d+)?)\.\.(\d+(?:\.\d+)?)'
        size_match = re.search(size_pattern, query)
        if size_match:
            params['min_size_mb'] = float(size_match.group(1))
            params['max_size_mb'] = float(size_match.group(2))
            
        # Custom field pattern
        custom_pattern = r'(\w+):([^:\s]+)'
        custom_matches = re.finditer(custom_pattern, query)
        for match in custom_matches:
            field_name = match.group(1)
            field_value = match.group(2)
            # Skip already processed special fields
            if field_name not in ['type', 'date', 'size']:
                params[f'custom_{field_name}'] = field_value
                
        return params
        
    def execute_metadata_query(self, query: str) -> List[str]:
        """
        Execute a metadata query string and return matching document IDs
        
        Args:
            query: Metadata query string
            
        Returns:
            List of document IDs matching the query
        """
        params = self.parse_metadata_query(query)
        result_sets = []
        
        # Process file types
        if 'file_types' in params:
            result_sets.append(self.search_by_file_type(params['file_types']))
            
        # Process date range
        if 'start_date' in params and 'end_date' in params:
            result_sets.append(self.search_by_date_range(params['start_date'], params['end_date']))
            
        # Process size range
        if 'min_size_mb' in params and 'max_size_mb' in params:
            result_sets.append(self.search_by_size_range(params['min_size_mb'], params['max_size_mb']))
            
        # Process custom fields
        for param_name, param_value in params.items():
            if param_name.startswith('custom_'):
                field_name = param_name[7:]  # Remove 'custom_' prefix
                result_sets.append(self.search_by_custom_field(field_name, param_value))
                
        # Combine results (AND operation by default)
        return self.combine_search_results(result_sets, operation="and")

# Factory function to get a metadata search engine instance
def get_metadata_search_engine(metadata_path: Optional[str] = None) -> MetadataSearchEngine:
    """
    Get a metadata search engine instance
    
    Args:
        metadata_path: Path to the metadata store
        
    Returns:
        MetadataSearchEngine instance
    """
    return MetadataSearchEngine(metadata_path)
