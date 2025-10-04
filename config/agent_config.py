# Agent Assistant Configuration

# Set to True to use the enhanced version with multi-source search
USE_ENHANCED_AGENT = True

# Configuration for multi-source search
MULTI_SOURCE_SEARCH_CONFIG = {
    "max_results_per_source": 5,
    "enable_web_search": True,
    "enable_structured_data": True,
    "enable_api_search": False,  # Set to True when API connectors are configured
    "search_timeout": 15,  # Maximum seconds to wait for search results
    "cache_results": True,  # Cache search results for improved performance
}

# Knowledge source configurations
KNOWLEDGE_SOURCES = {
    "Indexed Documents": {
        "enabled": True,
        "description": "Local vector database of indexed documents",
        "priority": 1
    },
    "Web Search (External)": {
        "enabled": True,
        "description": "Search the web for up-to-date information",
        "priority": 2
    },
    "Structured Data (External)": {
        "enabled": True,
        "description": "Structured databases and tables",
        "priority": 3
    },
    "API Data (External)": {
        "enabled": False,
        "description": "Information from external APIs",
        "priority": 4
    },
    "Enterprise Data": {
        "enabled": False,
        "description": "Internal enterprise data sources",
        "priority": 5
    },
    "Internal Wiki": {
        "enabled": False,
        "description": "Company wiki and documentation",
        "priority": 6
    }
}
