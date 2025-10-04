"""
Weaviate Configuration Management
Centralized configuration for Weaviate integration
"""
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class WeaviateConfig:
    """Weaviate configuration settings"""
    url: str = "http://localhost:8080"
    api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    timeout: int = 30
    batch_size: int = 100
    default_vectorizer: str = "text2vec-openai"
    enable_hybrid_search: bool = True
    
    @classmethod
    def from_env(cls) -> 'WeaviateConfig':
        """Load configuration from environment variables"""
        return cls(
            url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
            api_key=os.getenv("WEAVIATE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            timeout=int(os.getenv("WEAVIATE_TIMEOUT", "30")),
            batch_size=int(os.getenv("WEAVIATE_BATCH_SIZE", "100")),
            default_vectorizer=os.getenv("WEAVIATE_VECTORIZER", "text2vec-openai"),
            enable_hybrid_search=os.getenv("WEAVIATE_HYBRID_SEARCH", "true").lower() == "true"
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'WeaviateConfig':
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            return cls(**config_data.get("weaviate", {}))
        except Exception:
            return cls.from_env()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "url": self.url,
            "api_key": self.api_key,
            "openai_api_key": self.openai_api_key,
            "timeout": self.timeout,
            "batch_size": self.batch_size,
            "default_vectorizer": self.default_vectorizer,
            "enable_hybrid_search": self.enable_hybrid_search
        }

# Collection schemas for different data types
COLLECTION_SCHEMAS = {
    "documents": {
        "description": "General document storage",
        "properties": {
            "title": {"data_type": "TEXT", "description": "Document title"},
            "file_path": {"data_type": "TEXT", "description": "Original file path"},
            "file_type": {"data_type": "TEXT", "description": "File type/extension"},
            "page_number": {"data_type": "INT", "description": "Page number for multi-page documents"}
        }
    },
    "web_content": {
        "description": "Web scraped content",
        "properties": {
            "url": {"data_type": "TEXT", "description": "Source URL"},
            "title": {"data_type": "TEXT", "description": "Web page title"},
            "domain": {"data_type": "TEXT", "description": "Website domain"},
            "scraped_at": {"data_type": "DATE", "description": "Scraping timestamp"}
        }
    },
    "chat_history": {
        "description": "Chat conversation history",
        "properties": {
            "user_id": {"data_type": "TEXT", "description": "User identifier"},
            "session_id": {"data_type": "TEXT", "description": "Chat session ID"},
            "message_type": {"data_type": "TEXT", "description": "user or assistant"},
            "timestamp": {"data_type": "DATE", "description": "Message timestamp"}
        }
    },
    "excel_data": {
        "description": "Excel file content and analysis",
        "properties": {
            "sheet_name": {"data_type": "TEXT", "description": "Excel sheet name"},
            "row_number": {"data_type": "INT", "description": "Row number"},
            "column_names": {"data_type": "TEXT[]", "description": "Column headers"},
            "data_type": {"data_type": "TEXT", "description": "Type of Excel data"}
        }
    },
    "powerbi_reports": {
        "description": "PowerBI report metadata and content",
        "properties": {
            "report_id": {"data_type": "TEXT", "description": "PowerBI report ID"},
            "workspace_id": {"data_type": "TEXT", "description": "PowerBI workspace ID"},
            "report_name": {"data_type": "TEXT", "description": "Report display name"},
            "dataset_id": {"data_type": "TEXT", "description": "Associated dataset ID"}
        }
    }
}

def get_weaviate_config() -> WeaviateConfig:
    """Get Weaviate configuration with fallback hierarchy"""
    
    # Try to load from config file first
    config_file = os.path.join(os.path.dirname(__file__), "weaviate.json")
    if os.path.exists(config_file):
        return WeaviateConfig.from_file(config_file)
    
    # Fall back to environment variables
    return WeaviateConfig.from_env()

def create_default_collections() -> Dict[str, Dict[str, Any]]:
    """Get default collection configurations"""
    return COLLECTION_SCHEMAS
