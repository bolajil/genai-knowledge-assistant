"""
Enterprise Metadata Filtering System

Implements advanced metadata filtering for precise document retrieval
with support for complex queries and filter combinations.
"""

import logging
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import re
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class FilterCriteria:
    """Filter criteria for document retrieval"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, not_in, contains, regex
    value: Any
    case_sensitive: bool = False
    
    def matches(self, document_metadata: Dict[str, Any]) -> bool:
        """Check if document metadata matches this filter criteria"""
        if self.field not in document_metadata:
            return False
        
        doc_value = document_metadata[self.field]
        filter_value = self.value
        
        # Handle case sensitivity for string comparisons
        if isinstance(doc_value, str) and isinstance(filter_value, str) and not self.case_sensitive:
            doc_value = doc_value.lower()
            filter_value = filter_value.lower()
        
        try:
            if self.operator == "eq":
                return doc_value == filter_value
            elif self.operator == "ne":
                return doc_value != filter_value
            elif self.operator == "gt":
                return doc_value > filter_value
            elif self.operator == "lt":
                return doc_value < filter_value
            elif self.operator == "gte":
                return doc_value >= filter_value
            elif self.operator == "lte":
                return doc_value <= filter_value
            elif self.operator == "in":
                return doc_value in filter_value
            elif self.operator == "not_in":
                return doc_value not in filter_value
            elif self.operator == "contains":
                return str(filter_value) in str(doc_value)
            elif self.operator == "regex":
                pattern = re.compile(str(filter_value), re.IGNORECASE if not self.case_sensitive else 0)
                return bool(pattern.search(str(doc_value)))
            else:
                logger.warning(f"Unknown operator: {self.operator}")
                return False
        except Exception as e:
            logger.error(f"Filter matching error: {e}")
            return False

@dataclass
class FilterGroup:
    """Group of filter criteria with logical operators"""
    criteria: List[FilterCriteria] = field(default_factory=list)
    operator: str = "AND"  # AND, OR
    
    def matches(self, document_metadata: Dict[str, Any]) -> bool:
        """Check if document metadata matches this filter group"""
        if not self.criteria:
            return True
        
        results = [criterion.matches(document_metadata) for criterion in self.criteria]
        
        if self.operator == "AND":
            return all(results)
        elif self.operator == "OR":
            return any(results)
        else:
            logger.warning(f"Unknown group operator: {self.operator}")
            return False

class EnterpriseMetadataFilter:
    """Enterprise-grade metadata filtering system"""
    
    def __init__(self):
        self.predefined_filters = {
            "legal_documents": FilterGroup([
                FilterCriteria("document_type", "eq", "legal"),
                FilterCriteria("chunk_type", "in", ["legal_section", "legal_subsection"])
            ], "AND"),
            
            "technical_docs": FilterGroup([
                FilterCriteria("document_type", "eq", "technical"),
                FilterCriteria("chunk_type", "contains", "technical")
            ], "AND"),
            
            "recent_content": FilterGroup([
                FilterCriteria("char_count", "gte", 100),
                FilterCriteria("word_count", "gte", 20)
            ], "AND"),
            
            "substantial_chunks": FilterGroup([
                FilterCriteria("char_count", "gte", 500)
            ]),
            
            "bylaw_articles": FilterGroup([
                FilterCriteria("source", "contains", "Article", False),
                FilterCriteria("document_type", "eq", "legal")
            ], "AND")
        }
    
    def filter_documents(
        self, 
        documents: List[Dict[str, Any]], 
        filters: Union[str, FilterGroup, List[FilterCriteria], Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Filter documents based on metadata criteria"""
        if not documents or not filters:
            return documents
        
        try:
            # Convert filters to FilterGroup
            filter_group = self._normalize_filters(filters)
            
            # Apply filters
            filtered_docs = []
            for doc in documents:
                metadata = doc.get('metadata', {})
                
                # Add document-level metadata
                if 'content' in doc:
                    metadata.update({
                        'char_count': len(doc['content']),
                        'word_count': len(doc['content'].split()),
                        'has_content': bool(doc['content'].strip())
                    })
                
                if filter_group.matches(metadata):
                    filtered_docs.append(doc)
            
            logger.info(f"Filtered {len(documents)} documents to {len(filtered_docs)} results")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Document filtering failed: {e}")
            return documents  # Return original documents on error
    
    def _normalize_filters(self, filters: Union[str, FilterGroup, List[FilterCriteria], Dict[str, Any]]) -> FilterGroup:
        """Convert various filter formats to FilterGroup"""
        if isinstance(filters, str):
            # Predefined filter name
            if filters in self.predefined_filters:
                return self.predefined_filters[filters]
            else:
                logger.warning(f"Unknown predefined filter: {filters}")
                return FilterGroup()
        
        elif isinstance(filters, FilterGroup):
            return filters
        
        elif isinstance(filters, list):
            # List of FilterCriteria
            return FilterGroup(filters, "AND")
        
        elif isinstance(filters, dict):
            # Dictionary format
            return self._dict_to_filter_group(filters)
        
        else:
            logger.warning(f"Unknown filter format: {type(filters)}")
            return FilterGroup()
    
    def _dict_to_filter_group(self, filter_dict: Dict[str, Any]) -> FilterGroup:
        """Convert dictionary to FilterGroup"""
        criteria = []
        
        for field, condition in filter_dict.items():
            if field in ["operator", "case_sensitive"]:
                continue
            
            if isinstance(condition, dict):
                # Complex condition: {"operator": "gte", "value": 100}
                operator = condition.get("operator", "eq")
                value = condition.get("value")
                case_sensitive = condition.get("case_sensitive", False)
                
                criteria.append(FilterCriteria(field, operator, value, case_sensitive))
            
            else:
                # Simple condition: field = value
                criteria.append(FilterCriteria(field, "eq", condition))
        
        operator = filter_dict.get("operator", "AND")
        return FilterGroup(criteria, operator)
    
    def create_article_filter(self, article_numbers: List[Union[str, int]]) -> FilterGroup:
        """Create filter for specific articles"""
        article_criteria = []
        
        for article_num in article_numbers:
            article_criteria.extend([
                FilterCriteria("article_number", "eq", article_num),
                FilterCriteria("article_title", "contains", f"Article {article_num}", False),
                FilterCriteria("source", "contains", f"Article {article_num}", False)
            ])
        
        return FilterGroup(article_criteria, "OR")
    
    def create_section_filter(self, section_numbers: List[Union[str, int]]) -> FilterGroup:
        """Create filter for specific sections"""
        section_criteria = []
        
        for section_num in section_numbers:
            section_criteria.extend([
                FilterCriteria("section_number", "eq", section_num),
                FilterCriteria("section", "contains", f"Section {section_num}", False),
                FilterCriteria("source", "contains", f"Section {section_num}", False)
            ])
        
        return FilterGroup(section_criteria, "OR")
    
    def create_content_quality_filter(self, min_chars: int = 200, min_words: int = 30) -> FilterGroup:
        """Create filter for content quality"""
        return FilterGroup([
            FilterCriteria("char_count", "gte", min_chars),
            FilterCriteria("word_count", "gte", min_words),
            FilterCriteria("has_content", "eq", True)
        ], "AND")
    
    def create_document_type_filter(self, doc_types: List[str]) -> FilterGroup:
        """Create filter for document types"""
        return FilterGroup([
            FilterCriteria("document_type", "in", doc_types)
        ])
    
    def combine_filters(self, filters: List[FilterGroup], operator: str = "AND") -> FilterGroup:
        """Combine multiple filter groups"""
        all_criteria = []
        for filter_group in filters:
            all_criteria.extend(filter_group.criteria)
        
        return FilterGroup(all_criteria, operator)
    
    def get_available_metadata_fields(self, documents: List[Dict[str, Any]]) -> Dict[str, set]:
        """Analyze documents to find available metadata fields and their values"""
        field_values = {}
        
        for doc in documents:
            metadata = doc.get('metadata', {})
            
            # Add computed fields
            if 'content' in doc:
                metadata.update({
                    'char_count': len(doc['content']),
                    'word_count': len(doc['content'].split())
                })
            
            for field, value in metadata.items():
                if field not in field_values:
                    field_values[field] = set()
                field_values[field].add(str(value))
        
        return field_values
    
    def suggest_filters(self, documents: List[Dict[str, Any]], query: str = None) -> List[str]:
        """Suggest relevant filters based on document analysis and query"""
        suggestions = []
        
        # Analyze available metadata
        field_values = self.get_available_metadata_fields(documents)
        
        # Document type suggestions
        if 'document_type' in field_values:
            doc_types = field_values['document_type']
            if 'legal' in doc_types:
                suggestions.append("legal_documents")
            if 'technical' in doc_types:
                suggestions.append("technical_docs")
        
        # Article/Section suggestions based on query
        if query:
            query_lower = query.lower()
            
            # Check for article references
            article_matches = re.findall(r'article\s+([ivx]+|\d+)', query_lower)
            if article_matches:
                suggestions.append(f"article_filter: {article_matches}")
            
            # Check for section references
            section_matches = re.findall(r'section\s+(\d+)', query_lower)
            if section_matches:
                suggestions.append(f"section_filter: {section_matches}")
        
        # Quality filters
        if len(documents) > 50:  # Large document set
            suggestions.append("substantial_chunks")
        
        return suggestions
    
    def export_filter_config(self, filter_group: FilterGroup, filename: str = None) -> str:
        """Export filter configuration to JSON"""
        config = {
            "filter_group": {
                "operator": filter_group.operator,
                "criteria": [
                    {
                        "field": criterion.field,
                        "operator": criterion.operator,
                        "value": criterion.value,
                        "case_sensitive": criterion.case_sensitive
                    }
                    for criterion in filter_group.criteria
                ]
            },
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                return f"Filter config exported to {filename}"
            except Exception as e:
                logger.error(f"Export failed: {e}")
                return f"Export failed: {e}"
        else:
            return json.dumps(config, indent=2, ensure_ascii=False)
    
    def load_filter_config(self, filename: str) -> Optional[FilterGroup]:
        """Load filter configuration from JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            filter_data = config.get("filter_group", {})
            criteria = []
            
            for criterion_data in filter_data.get("criteria", []):
                criteria.append(FilterCriteria(
                    field=criterion_data["field"],
                    operator=criterion_data["operator"],
                    value=criterion_data["value"],
                    case_sensitive=criterion_data.get("case_sensitive", False)
                ))
            
            return FilterGroup(criteria, filter_data.get("operator", "AND"))
            
        except Exception as e:
            logger.error(f"Failed to load filter config: {e}")
            return None

def get_enterprise_metadata_filter() -> EnterpriseMetadataFilter:
    """Get instance of enterprise metadata filter"""
    return EnterpriseMetadataFilter()

def filter_documents_by_metadata(
    documents: List[Dict[str, Any]], 
    filters: Union[str, Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Convenience function for filtering documents"""
    filter_system = get_enterprise_metadata_filter()
    return filter_system.filter_documents(documents, filters)

def create_legal_article_filter(article_numbers: List[Union[str, int]]) -> FilterGroup:
    """Convenience function to create legal article filter"""
    filter_system = get_enterprise_metadata_filter()
    return filter_system.create_article_filter(article_numbers)
