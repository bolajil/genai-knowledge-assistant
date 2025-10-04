"""
Model Context Protocol (MCP) Package
===================================
This package provides tools and utilities for the Model Context Protocol.
"""

from .logger import mcp_logger

# Import integration module to patch the auth middleware
try:
    from . import integration
except ImportError:
    pass

__all__ = ['mcp_logger']