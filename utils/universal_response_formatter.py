"""
Universal Response Formatter for All VaultMind Tabs
Works with: Query Assistant, Chat Assistant, Agent Assistant, and any other response-generating tabs
"""

import streamlit as st
from typing import Optional, Dict, List, Any, Callable
from utils.response_writer import rewrite_query_response
import logging

logger = logging.getLogger(__name__)


class UniversalResponseFormatter:
    """
    Universal response formatter that works across all VaultMind tabs
    Provides consistent formatting and user controls
    """
    
    def __init__(self, tab_name: str = "Response"):
        """
        Initialize formatter
        
        Args:
            tab_name: Name of the tab using this formatter
        """
        self.tab_name = tab_name
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for formatter settings"""
        if 'formatter_settings' not in st.session_state:
            st.session_state.formatter_settings = {
                'enabled': True,
                'use_llm': False,
                'add_enhancements': True,
                'show_metadata': True,
                'show_sources': True
            }
    
    def render_settings_ui(self, location: str = "sidebar"):
        """
        Render formatter settings UI
        
        Args:
            location: Where to render ('sidebar', 'expander', 'inline')
        """
        settings = st.session_state.formatter_settings
        
        if location == "sidebar":
            with st.sidebar:
                self._render_settings_controls(settings)
        elif location == "expander":
            with st.expander("📝 Response Formatting Settings"):
                self._render_settings_controls(settings)
        else:  # inline
            self._render_settings_controls(settings)
    
    def _render_settings_controls(self, settings: dict):
        """Render the actual settings controls"""
        st.subheader("📝 Response Formatting")
        
        settings['enabled'] = st.checkbox(
            "Enable formatted responses",
            value=settings.get('enabled', True),
            help="Rewrite responses in beautiful markdown format",
            key=f"{self.tab_name}_formatter_enabled"
        )
        
        if settings['enabled']:
            col1, col2 = st.columns(2)
            
            with col1:
                settings['use_llm'] = st.checkbox(
                    "🤖 LLM enhancement",
                    value=settings.get('use_llm', False),
                    help="Better quality (slower, ~$0.002 per response)",
                    key=f"{self.tab_name}_use_llm"
                )
                
                settings['show_sources'] = st.checkbox(
                    "📚 Show sources",
                    value=settings.get('show_sources', True),
                    help="Display source citations",
                    key=f"{self.tab_name}_show_sources"
                )
            
            with col2:
                settings['add_enhancements'] = st.checkbox(
                    "✨ Enhancements",
                    value=settings.get('add_enhancements', True),
                    help="TOC, syntax highlighting, etc.",
                    key=f"{self.tab_name}_enhancements"
                )
                
                settings['show_metadata'] = st.checkbox(
                    "ℹ️ Show metadata",
                    value=settings.get('show_metadata', True),
                    help="Display query information",
                    key=f"{self.tab_name}_show_metadata"
                )
    
    def format_response(
        self,
        raw_response: str,
        query: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format response based on current settings
        
        Args:
            raw_response: Original response text
            query: User's query/input
            sources: List of source documents
            metadata: Additional metadata
        
        Returns:
            Formatted response (or original if formatting disabled)
        """
        settings = st.session_state.formatter_settings
        
        # If formatting disabled, return original
        if not settings.get('enabled', True):
            return raw_response
        
        # Filter sources/metadata based on settings
        final_sources = sources if settings.get('show_sources', True) else None
        final_metadata = metadata if settings.get('show_metadata', True) else None
        
        try:
            formatted = rewrite_query_response(
                raw_response=raw_response,
                query=query,
                sources=final_sources,
                metadata=final_metadata,
                use_llm=settings.get('use_llm', False),
                enhance=settings.get('add_enhancements', True)
            )
            return formatted
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return raw_response  # Fallback to original
    
    def display_response(
        self,
        raw_response: str,
        query: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        show_comparison: bool = False
    ):
        """
        Format and display response
        
        Args:
            raw_response: Original response text
            query: User's query/input
            sources: List of source documents
            metadata: Additional metadata
            show_comparison: Show side-by-side comparison
        """
        settings = st.session_state.formatter_settings
        
        if show_comparison and settings.get('enabled', True):
            # Side-by-side comparison
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📄 Original Response")
                st.markdown(raw_response)
            
            with col2:
                st.subheader("📝 Formatted Response")
                formatted = self.format_response(raw_response, query, sources, metadata)
                st.markdown(formatted)
        else:
            # Single response
            formatted = self.format_response(raw_response, query, sources, metadata)
            st.markdown(formatted)


# Global formatter instances for each tab
_formatters = {}

def get_formatter(tab_name: str) -> UniversalResponseFormatter:
    """
    Get or create formatter for a specific tab
    
    Args:
        tab_name: Name of the tab
    
    Returns:
        UniversalResponseFormatter instance
    """
    if tab_name not in _formatters:
        _formatters[tab_name] = UniversalResponseFormatter(tab_name)
    return _formatters[tab_name]


# Convenience functions for quick integration

def format_and_display(
    raw_response: str,
    query: str,
    tab_name: str = "Response",
    sources: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    show_comparison: bool = False
):
    """
    Quick function to format and display response
    
    Args:
        raw_response: Original response text
        query: User's query/input
        tab_name: Name of the tab
        sources: List of source documents
        metadata: Additional metadata
        show_comparison: Show side-by-side comparison
    """
    formatter = get_formatter(tab_name)
    formatter.display_response(raw_response, query, sources, metadata, show_comparison)


def add_formatter_settings(tab_name: str = "Response", location: str = "sidebar"):
    """
    Quick function to add formatter settings UI
    
    Args:
        tab_name: Name of the tab
        location: Where to render ('sidebar', 'expander', 'inline')
    """
    formatter = get_formatter(tab_name)
    formatter.render_settings_ui(location)


def format_response_simple(
    raw_response: str,
    query: str,
    tab_name: str = "Response"
) -> str:
    """
    Simplest way to format a response
    
    Args:
        raw_response: Original response text
        query: User's query/input
        tab_name: Name of the tab
    
    Returns:
        Formatted response
    """
    formatter = get_formatter(tab_name)
    return formatter.format_response(raw_response, query)
