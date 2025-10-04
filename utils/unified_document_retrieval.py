"""
Unified Document Retrieval System
=================================

Centralized retrieval system for all tabs (Query, Chat, Agent) to ensure consistency.
Generic approach that reads any document content without pre-assumptions.
"""

import logging
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import os

logger = logging.getLogger(__name__)

class UnifiedDocumentRetriever:
    """
    Centralized document retrieval system that works with any document type
    without making assumptions about content structure.
    """
    
    def __init__(self):
        self.base_paths = [
            Path("data/indexes"),
            Path("data/faiss_index"), 
            Path("data")
        ]
        self.supported_extensions = ['.txt', '.json', '.md', '.html', '.csv']
        
    def find_index_path(self, index_name: str) -> Optional[Path]:
        """Find the path to an index directory without assumptions."""
        possible_names = [
            index_name,
            f"{index_name}_index",
            index_name.replace("_index", ""),
            index_name.replace("index", "").strip("_")
        ]
        
        for base_path in self.base_paths:
            if not base_path.exists():
                continue
                
            for name in possible_names:
                index_path = base_path / name
                if index_path.exists() and index_path.is_dir():
                    logger.info(f"Found index at: {index_path}")
                    return index_path
        
        logger.warning(f"Index '{index_name}' not found in any location")
        return None
    
    def discover_content_files(self, index_path: Path) -> List[Path]:
        """Discover all readable content files in an index directory."""
        content_files = []
        
        # Look for common content files
        priority_files = [
            "extracted_text.txt",
            "content.txt", 
            "document.txt",
            "text.txt"
        ]
        
        # Check priority files first
        for filename in priority_files:
            file_path = index_path / filename
            if file_path.exists():
                content_files.append(file_path)
        
        # Find all other supported files
        for ext in self.supported_extensions:
            for file_path in index_path.glob(f"*{ext}"):
                if file_path.name not in ["index.meta", "chunks_metadata.json"] and file_path not in content_files:
                    content_files.append(file_path)
        
        # Also check semantic chunk files
        semantic_chunks = list(index_path.glob("semantic_chunk_*.json"))
        if semantic_chunks:
            logger.info(f"Found {len(semantic_chunks)} semantic chunk files")
            content_files.extend(semantic_chunks[:10])  # Limit to avoid too many files
        
        logger.info(f"Discovered {len(content_files)} content files in {index_path.name}")
        return content_files
    
    def read_file_content(self, file_path: Path) -> Optional[str]:
        """Read content from any supported file type."""
        try:
            if file_path.suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, dict):
                    if 'content' in data:
                        return data['content']
                    elif 'text' in data:
                        return data['text']
                    elif 'data' in data:
                        return str(data['data'])
                    else:
                        # Return all text values concatenated
                        text_parts = []
                        for key, value in data.items():
                            if isinstance(value, str) and len(value) > 10:
                                text_parts.append(f"{key}: {value}")
                        return '\n'.join(text_parts)
                elif isinstance(data, list):
                    # Handle list of objects
                    text_parts = []
                    for item in data:
                        if isinstance(item, dict):
                            for key, value in item.items():
                                if isinstance(value, str) and len(value) > 10:
                                    text_parts.append(value)
                        elif isinstance(item, str):
                            text_parts.append(item)
                    return '\n'.join(text_parts)
                else:
                    return str(data)
            
            else:
                # Handle text files
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
    
    def extract_relevant_content(self, content: str, query: str, max_length: int = 2000) -> List[Dict[str, Any]]:
        """Extract relevant content sections based on query without assumptions."""
        if not content or not query:
            return []
        
        query_terms = [term.lower().strip() for term in query.split() if len(term) > 2]
        if not query_terms:
            return [{"content": content[:max_length], "relevance_score": 0.1, "method": "fallback"}]
        
        results = []
        
        # Method 1: Page-based extraction (if page markers exist)
        if "--- Page" in content:
            pages = content.split("--- Page")
            for i, page in enumerate(pages[1:], 1):  # Skip first empty split
                page_content = page.strip()
                if not page_content:
                    continue
                
                # Calculate relevance score
                page_lower = page_content.lower()
                score = 0
                matched_terms = []
                
                for term in query_terms:
                    count = page_lower.count(term)
                    if count > 0:
                        score += count * 10
                        matched_terms.append(term)
                
                if score > 0:
                    # Extract relevant sentences
                    sentences = page_content.split('.')
                    relevant_sentences = []
                    
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if any(term in sentence_lower for term in matched_terms):
                            relevant_sentences.append(sentence.strip())
                    
                    if relevant_sentences:
                        extracted_content = '. '.join(relevant_sentences[:5])
                        if len(extracted_content) > max_length:
                            extracted_content = extracted_content[:max_length] + "..."
                        
                        results.append({
                            "content": extracted_content,
                            "relevance_score": min(score / 100, 1.0),
                            "page": i,
                            "matched_terms": matched_terms,
                            "method": "page_based"
                        })
        
        # Method 2: Paragraph-based extraction
        if not results:
            paragraphs = content.split('\n\n')
            for i, paragraph in enumerate(paragraphs):
                if len(paragraph) < 50:  # Skip very short paragraphs
                    continue
                
                paragraph_lower = paragraph.lower()
                score = 0
                matched_terms = []
                
                for term in query_terms:
                    count = paragraph_lower.count(term)
                    if count > 0:
                        score += count * 5
                        matched_terms.append(term)
                
                if score > 0:
                    content_snippet = paragraph[:max_length] + "..." if len(paragraph) > max_length else paragraph
                    
                    results.append({
                        "content": content_snippet,
                        "relevance_score": min(score / 50, 1.0),
                        "paragraph": i + 1,
                        "matched_terms": matched_terms,
                        "method": "paragraph_based"
                    })
        
        # Method 3: Sentence-based extraction (fallback)
        if not results:
            sentences = content.split('.')
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                
                sentence_lower = sentence.lower()
                matched_terms = [term for term in query_terms if term in sentence_lower]
                
                if matched_terms:
                    # Get context (previous and next sentences)
                    start_idx = max(0, i - 1)
                    end_idx = min(len(sentences), i + 3)
                    context_sentences = sentences[start_idx:end_idx]
                    context_content = '. '.join(s.strip() for s in context_sentences if s.strip())
                    
                    if len(context_content) > max_length:
                        context_content = context_content[:max_length] + "..."
                    
                    results.append({
                        "content": context_content,
                        "relevance_score": len(matched_terms) / len(query_terms),
                        "sentence": i + 1,
                        "matched_terms": matched_terms,
                        "method": "sentence_based"
                    })
        
        # Sort by relevance score and return top results
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:5]  # Return top 5 results
    
    def search_index(self, query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Main search method that works with any index structure.
        
        Args:
            query: Search query
            index_name: Name of the index to search
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with content and metadata
        """
        # Find the index path
        index_path = self.find_index_path(index_name)
        if not index_path:
            return [{
                "content": f"Index '{index_name}' not found",
                "source": "error",
                "relevance_score": 0.0,
                "error": True
            }]
        
        # Discover content files
        content_files = self.discover_content_files(index_path)
        if not content_files:
            return [{
                "content": f"No readable content files found in index '{index_name}'",
                "source": "error", 
                "relevance_score": 0.0,
                "error": True
            }]
        
        all_results = []
        
        # Process each content file
        for file_path in content_files:
            content = self.read_file_content(file_path)
            if not content:
                continue
            
            # Extract relevant content
            file_results = self.extract_relevant_content(content, query)
            
            # Add file metadata to results
            for result in file_results:
                result.update({
                    "source": f"{index_name}/{file_path.name}",
                    "file_type": file_path.suffix,
                    "index_name": index_name
                })
                all_results.append(result)
        
        # Remove duplicates and sort by relevance
        unique_results = self.remove_duplicate_results(all_results)
        unique_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Format results for consistency
        formatted_results = []
        for result in unique_results[:max_results]:
            formatted_results.append({
                "content": result["content"],
                "source": result["source"],
                "relevance_score": result["relevance_score"],
                "metadata": {
                    "method": result.get("method", "unknown"),
                    "matched_terms": result.get("matched_terms", []),
                    "page": result.get("page"),
                    "paragraph": result.get("paragraph"),
                    "sentence": result.get("sentence"),
                    "file_type": result.get("file_type"),
                    "index_name": result.get("index_name")
                }
            })
        
        logger.info(f"Retrieved {len(formatted_results)} results for query '{query}' from index '{index_name}'")
        return formatted_results
    
    def remove_duplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on content similarity."""
        unique_results = []
        
        for result in results:
            is_duplicate = False
            result_words = set(result["content"].lower().split())
            
            for existing in unique_results:
                existing_words = set(existing["content"].lower().split())
                
                # Calculate Jaccard similarity
                intersection = len(result_words & existing_words)
                union = len(result_words | existing_words)
                
                if union > 0 and intersection / union > 0.7:  # 70% similarity threshold
                    is_duplicate = True
                    # Keep the result with higher relevance score
                    if result["relevance_score"] > existing["relevance_score"]:
                        unique_results.remove(existing)
                        unique_results.append(result)
                    break
            
            if not is_duplicate:
                unique_results.append(result)
        
        return unique_results

# Global instance for use across all tabs
unified_retriever = UnifiedDocumentRetriever()

def search_documents(query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Unified search function for use by all tabs (Query, Chat, Agent).
    
    Args:
        query: Search query
        index_name: Name of the index to search  
        max_results: Maximum number of results to return
        
    Returns:
        List of search results with content and metadata
    """
    return unified_retriever.search_index(query, index_name, max_results)

def get_available_indexes() -> List[str]:
    """Get list of all available indexes."""
    available_indexes = []
    
    for base_path in unified_retriever.base_paths:
        if not base_path.exists():
            continue
            
        for item in base_path.iterdir():
            if item.is_dir():
                # Check if directory contains any readable content
                content_files = unified_retriever.discover_content_files(item)
                if content_files:
                    available_indexes.append(item.name)
    
    return sorted(list(set(available_indexes)))

def validate_index(index_name: str) -> Dict[str, Any]:
    """Validate an index and return status information."""
    index_path = unified_retriever.find_index_path(index_name)
    
    if not index_path:
        return {
            "valid": False,
            "error": f"Index '{index_name}' not found",
            "path": None,
            "content_files": []
        }
    
    content_files = unified_retriever.discover_content_files(index_path)
    
    return {
        "valid": len(content_files) > 0,
        "error": None if content_files else "No readable content files found",
        "path": str(index_path),
        "content_files": [f.name for f in content_files],
        "file_count": len(content_files)
    }
