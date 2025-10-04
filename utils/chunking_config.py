"""
Centralized Chunking Configuration

This module provides a centralized configuration system for document chunking
across all retrieval systems in the VaultMind GenAI Knowledge Assistant.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Global chunking configuration
DOCUMENT_CHUNKING_OPTIONS = {
    "chunk_size": 1500,
    "chunk_overlap": 500,
    "respect_section_breaks": True,
    "extract_tables": True,
    "preserve_heading_structure": True
}

def get_chunking_config() -> Dict[str, Any]:
    """Get the current chunking configuration"""
    return DOCUMENT_CHUNKING_OPTIONS.copy()

def update_chunking_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the global chunking configuration
    
    Args:
        new_config: Dictionary with new configuration values
        
    Returns:
        Updated configuration dictionary
    """
    global DOCUMENT_CHUNKING_OPTIONS
    
    # Validate configuration values
    if 'chunk_size' in new_config:
        if not isinstance(new_config['chunk_size'], int) or new_config['chunk_size'] < 100:
            raise ValueError("chunk_size must be an integer >= 100")
    
    if 'chunk_overlap' in new_config:
        if not isinstance(new_config['chunk_overlap'], int) or new_config['chunk_overlap'] < 0:
            raise ValueError("chunk_overlap must be a non-negative integer")
    
    # Update configuration
    DOCUMENT_CHUNKING_OPTIONS.update(new_config)
    
    logger.info(f"Chunking configuration updated: {DOCUMENT_CHUNKING_OPTIONS}")
    return DOCUMENT_CHUNKING_OPTIONS.copy()

def get_optimized_config_for_document_type(doc_type: str) -> Dict[str, Any]:
    """
    Get optimized chunking configuration for specific document types
    
    Args:
        doc_type: Type of document ('legal', 'technical', 'general', 'table_heavy')
        
    Returns:
        Optimized configuration dictionary
    """
    base_config = get_chunking_config()
    
    if doc_type == 'legal':
        # Legal documents benefit from larger chunks to preserve context
        base_config.update({
            "chunk_size": 2000,
            "chunk_overlap": 600,
            "respect_section_breaks": True,
            "preserve_heading_structure": True
        })
    elif doc_type == 'technical':
        # Technical docs need structured processing
        base_config.update({
            "chunk_size": 1500,
            "chunk_overlap": 400,
            "extract_tables": True,
            "preserve_heading_structure": True
        })
    elif doc_type == 'table_heavy':
        # Documents with many tables
        base_config.update({
            "chunk_size": 1200,
            "chunk_overlap": 300,
            "extract_tables": True,
            "respect_section_breaks": True
        })
    elif doc_type == 'general':
        # Use default configuration
        pass
    
    return base_config

def validate_chunking_config(config: Dict[str, Any]) -> bool:
    """
    Validate chunking configuration parameters
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    required_keys = ['chunk_size', 'chunk_overlap']
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    
    if config['chunk_size'] < 100:
        raise ValueError("chunk_size must be at least 100 characters")
    
    if config['chunk_overlap'] < 0:
        raise ValueError("chunk_overlap cannot be negative")
    
    if config['chunk_overlap'] >= config['chunk_size']:
        raise ValueError("chunk_overlap must be less than chunk_size")
    
    return True

def get_chunking_summary() -> Dict[str, Any]:
    """Get a summary of current chunking configuration and its implications"""
    config = get_chunking_config()
    
    # Calculate some metrics
    effective_chunk_size = config['chunk_size'] - config['chunk_overlap']
    overlap_percentage = (config['chunk_overlap'] / config['chunk_size']) * 100
    
    return {
        'current_config': config,
        'effective_chunk_size': effective_chunk_size,
        'overlap_percentage': round(overlap_percentage, 1),
        'implications': {
            'context_preservation': 'High' if config['chunk_overlap'] > 300 else 'Medium' if config['chunk_overlap'] > 100 else 'Low',
            'retrieval_precision': 'High' if config['chunk_size'] < 2000 else 'Medium' if config['chunk_size'] < 3000 else 'Low',
            'processing_efficiency': 'Low' if config['chunk_size'] > 2000 else 'Medium' if config['chunk_size'] > 1000 else 'High'
        },
        'recommendations': _get_config_recommendations(config)
    }

def _get_config_recommendations(config: Dict[str, Any]) -> list:
    """Get recommendations based on current configuration"""
    recommendations = []
    
    if config['chunk_overlap'] > config['chunk_size'] * 0.5:
        recommendations.append("Consider reducing chunk_overlap - very high overlap may cause redundancy")
    
    if config['chunk_size'] > 3000:
        recommendations.append("Large chunk_size may reduce retrieval precision")
    
    if config['chunk_size'] < 500:
        recommendations.append("Small chunk_size may fragment content and lose context")
    
    if config['chunk_overlap'] < 100:
        recommendations.append("Low chunk_overlap may cause context loss between chunks")
    
    if not recommendations:
        recommendations.append("Current configuration appears well-balanced")
    
    return recommendations

# Export the current configuration for easy access
__all__ = [
    'DOCUMENT_CHUNKING_OPTIONS',
    'get_chunking_config',
    'update_chunking_config',
    'get_optimized_config_for_document_type',
    'validate_chunking_config',
    'get_chunking_summary'
]
