"""
Unified Content Generator with ByLaw Document Optimization

This module provides an optimized content generation system that prioritizes
document content from ByLaw documents to ensure accurate responses.
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional, Union
import json

# Configure logging
logger = logging.getLogger(__name__)

# Try to import LLM components
try:
    from app.llm.provider import get_llm_provider
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger.warning("LLM provider not available, content generation will be limited")

def generate_content_with_search_results(
    query: str, 
    search_results: List[Any], 
    operation_type: str = "answer",
    format_type: str = "markdown",
    **kwargs
) -> str:
    """
    Generate content based on search results with optimization for ByLaw documents
    
    Args:
        query: User query
        search_results: List of search results
        operation_type: Type of content to generate (answer, summary, research)
        format_type: Output format (markdown, html, text)
        
    Returns:
        Generated content
    """
    # Check if we have any results with actual content
    has_valid_content = False
    for result in search_results:
        content = getattr(result, "content", None)
        if content and isinstance(content, str) and len(content.strip()) > 20:
            has_valid_content = True
            break
    
    # If no valid content, provide a fallback response
    if not has_valid_content:
        return "I don't have enough information from the documents to provide a reliable answer. The search results did not contain sufficient content to analyze."
    
    # Extract content from search results
    documents = []
    for result in search_results:
        # Extract content and source
        content = getattr(result, "content", "")
        source = getattr(result, "source_name", "Unknown")
        
        # Skip empty or very short content
        if not content or len(content.strip()) < 10:
            continue
        
        # Add to documents
        documents.append({
            "content": content,
            "source": source
        })
    
    # Check if we have any ByLaw documents
    bylaw_documents = [doc for doc in documents if "bylaw" in doc["source"].lower()]
    
    # If we have ByLaw documents, prioritize them
    if bylaw_documents:
        logger.info("Found ByLaw documents, prioritizing them for content generation")
        documents = bylaw_documents + [doc for doc in documents if doc not in bylaw_documents]
    
    # Prepare document content for prompt
    document_content = ""
    for i, doc in enumerate(documents):
        document_content += f"\nDOCUMENT {i+1}: {doc['source']}\n{doc['content']}\n"
    
    # Create a prompt that strongly emphasizes using document content
    prompt = f"""You are a knowledgeable assistant tasked with answering questions based ONLY on the document content provided.

QUESTION: {query}

DOCUMENT CONTENT:
{document_content}

IMPORTANT INSTRUCTIONS:
1. Answer ONLY based on the information in the documents provided.
2. If the documents don't contain the answer, say "I don't have enough information in the documents to answer that question."
3. DO NOT make up or infer information that is not explicitly stated in the documents.
4. Cite specific sections or quotes from the documents when possible.
5. Format your answer in {format_type} format.

Your answer:"""
    
    # Generate content using LLM
    if LLM_AVAILABLE:
        try:
            llm_provider = get_llm_provider()
            response = llm_provider.generate_content(prompt, max_tokens=1000)
            return response
        except Exception as e:
            logger.error(f"Error generating content with LLM: {e}")
            
            # Fall back to simple content generation
            return generate_simple_content(query, documents)
    else:
        # Fall back to simple content generation
        return generate_simple_content(query, documents)

def generate_simple_content(query: str, documents: List[Dict]) -> str:
    """Generate simple content when LLM is not available"""
    if not documents:
        return "No relevant information found in the documents."
    
    # Extract the most relevant document
    most_relevant = documents[0]
    
    # Return a simple response
    return f"""Based on the available document information:

{most_relevant['content']}

This information is from: {most_relevant['source']}"""

def generate_document_summary(document_content: str, **kwargs) -> str:
    """Generate a summary of document content"""
    if not document_content or len(document_content.strip()) < 20:
        return "No valid document content to summarize."
    
    # Create a prompt for document summarization
    prompt = f"""Summarize the following document content concisely while retaining all key information:

{document_content}

Summary:"""
    
    # Generate summary using LLM
    if LLM_AVAILABLE:
        try:
            llm_provider = get_llm_provider()
            response = llm_provider.generate_content(prompt, max_tokens=500)
            return response
        except Exception as e:
            logger.error(f"Error generating summary with LLM: {e}")
            
            # Fall back to simple summary
            return document_content[:500] + "... (summary truncated)"
    else:
        # Fall back to simple summary
        return document_content[:500] + "... (summary truncated)"

def generate_research_content(query: str, search_results: List[Any], **kwargs) -> str:
    """Generate comprehensive research content"""
    # This is just a wrapper around the main content generator with research-specific parameters
    return generate_content_with_search_results(
        query=query, 
        search_results=search_results, 
        operation_type="research",
        format_type="markdown",
        **kwargs
    )
