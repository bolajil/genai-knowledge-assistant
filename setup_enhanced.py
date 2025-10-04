"""
VaultMIND Knowledge Assistant - Enhanced Installation Script

This script helps set up the enhanced VaultMIND Knowledge Assistant.
It creates necessary directories, installs dependencies, and configures settings.
"""

import os
import sys
import subprocess
import logging
import json
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('setup.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
REQUIRED_DIRS = [
    "data/uploads",
    "data/faiss_index",
    "data/metadata",
    "data/feedback",
    "utils",
    "api",
    "tabs",
    "config"
]

BASIC_REQUIREMENTS = [
    "streamlit",
    "fastapi",
    "uvicorn",
    "pydantic",
    "requests",
    "pandas"
]

VECTOR_DB_REQUIREMENTS = [
    "faiss-cpu",
    "sentence-transformers"
]

LLM_REQUIREMENTS = [
    "openai",
    "anthropic"
]

LANGCHAIN_REQUIREMENTS = [
    "langchain",
    "langchain-community",
    "langchain-huggingface"
]

DOCUMENT_PROCESSING_REQUIREMENTS = [
    "pypdf",
    "docx2txt",
    "html2text",
    "markdown",
    "openpyxl"
]

def create_directories():
    """Create required directories"""
    logger.info("Creating required directories...")
    
    for directory in REQUIRED_DIRS:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {path}")
    
    logger.info("All required directories created successfully")

def install_dependencies(requirements, optional=False):
    """Install Python dependencies"""
    try:
        logger.info(f"Installing {'optional' if optional else 'required'} dependencies: {', '.join(requirements)}")
        
        command = [sys.executable, "-m", "pip", "install"] + requirements
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            if optional:
                logger.warning(f"Failed to install optional dependencies: {stderr.decode()}")
                return False
            else:
                logger.error(f"Failed to install required dependencies: {stderr.decode()}")
                sys.exit(1)
        
        logger.info(f"Successfully installed {'optional' if optional else 'required'} dependencies")
        return True
    
    except Exception as e:
        if optional:
            logger.warning(f"Error installing optional dependencies: {str(e)}")
            return False
        else:
            logger.error(f"Error installing required dependencies: {str(e)}")
            sys.exit(1)

def create_config_files():
    """Create configuration files"""
    logger.info("Creating configuration files...")
    
    # Vector DB configuration
    vector_db_config = {
        "default_provider": "faiss",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "vector_db_path": "data/faiss_index",
        "providers": {
            "faiss": {
                "enabled": True,
                "path": "data/faiss_index"
            },
            "chroma": {
                "enabled": False,
                "path": "data/chroma_db"
            },
            "weaviate": {
                "enabled": False,
                "url": "http://localhost:8080",
                "api_key": ""
            }
        }
    }
    
    with open('config/vector_db_config.py', 'w') as f:
        f.write("""\"\"\"
Vector Database Configuration
\"\"\"

def get_vector_db_config():
    \"\"\"Get the vector database configuration\"\"\"
    return {
        "default_provider": "faiss",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "vector_db_path": "data/faiss_index",
        "providers": {
            "faiss": {
                "enabled": True,
                "path": "data/faiss_index"
            },
            "chroma": {
                "enabled": False,
                "path": "data/chroma_db"
            },
            "weaviate": {
                "enabled": False,
                "url": "http://localhost:8080",
                "api_key": ""
            }
        }
    }

# Vector database types
class VectorDBType:
    FAISS = "faiss"
    CHROMA = "chroma"
    WEAVIATE = "weaviate"
""")
    
    logger.info("Created vector_db_config.py")
    
    # LLM configuration
    llm_config = {
        "default_provider": "openai",
        "openai": {
            "model": "gpt-4",
            "temperature": 0.3,
            "max_tokens": 1000
        },
        "claude": {
            "model": "claude-3-sonnet-20240229",
            "temperature": 0.3,
            "max_tokens": 1000
        },
        "deepseek": {
            "model": "deepseek-chat",
            "temperature": 0.3,
            "max_tokens": 1000
        }
    }
    
    with open('config/llm_config.yml', 'w') as f:
        f.write("""# LLM Configuration

default_provider: openai

openai:
  model: gpt-4
  temperature: 0.3
  max_tokens: 1000

claude:
  model: claude-3-sonnet-20240229
  temperature: 0.3
  max_tokens: 1000

deepseek:
  model: deepseek-chat
  temperature: 0.3
  max_tokens: 1000
""")
    
    logger.info("Created llm_config.yml")
    
    logger.info("All configuration files created successfully")

def create_sample_document():
    """Create a sample document for testing"""
    logger.info("Creating sample document...")
    
    sample_text = """# VaultMIND Knowledge Assistant

## Introduction

VaultMIND Knowledge Assistant is a powerful tool for ingesting, processing, and querying documents using vector embeddings and large language models (LLMs).

## Features

- Multi-format document processing
- Semantic search capabilities
- LLM-powered answering
- Metadata management
- User feedback collection

## Benefits of Knowledge Management

Effective knowledge management provides several benefits:

1. Improved information retrieval
2. Reduced time spent searching for information
3. Preservation of institutional knowledge
4. Enhanced decision-making
5. Increased productivity

## Getting Started

To get started with VaultMIND, follow these steps:

1. Ingest your documents
2. Ask questions in natural language
3. Get accurate answers with source citations
4. Provide feedback to improve results
"""
    
    sample_path = Path("data/uploads/sample_document.md")
    with open(sample_path, 'w') as f:
        f.write(sample_text)
    
    logger.info(f"Created sample document at {sample_path}")

def create_env_file():
    """Create .env file template"""
    logger.info("Creating .env file template...")
    
    env_content = """# API Keys for LLM Providers
OPENAI_API_KEY=your_openai_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Application Settings
PORT=8000
DEBUG=True
LOG_LEVEL=INFO

# Vector Database Settings
VECTOR_DB_PATH=data/faiss_index
"""
    
    with open('.env.template', 'w') as f:
        f.write(env_content)
    
    logger.info("Created .env.template file")

def main():
    """Main installation function"""
    logger.info("Starting VaultMIND Knowledge Assistant enhanced setup...")
    
    # Create directories
    create_directories()
    
    # Install basic requirements
    install_dependencies(BASIC_REQUIREMENTS)
    
    # Install optional dependencies
    vector_db_installed = install_dependencies(VECTOR_DB_REQUIREMENTS, optional=True)
    llm_installed = install_dependencies(LLM_REQUIREMENTS, optional=True)
    langchain_installed = install_dependencies(LANGCHAIN_REQUIREMENTS, optional=True)
    doc_processing_installed = install_dependencies(DOCUMENT_PROCESSING_REQUIREMENTS, optional=True)
    
    # Create configuration files
    create_config_files()
    
    # Create sample document
    create_sample_document()
    
    # Create .env file template
    create_env_file()
    
    # Display setup summary
    logger.info("\n=== VaultMIND Knowledge Assistant Setup Summary ===")
    logger.info("Directories created: ✅")
    logger.info(f"Basic requirements: ✅")
    logger.info(f"Vector database requirements: {'✅' if vector_db_installed else '❌'}")
    logger.info(f"LLM requirements: {'✅' if llm_installed else '❌'}")
    logger.info(f"LangChain requirements: {'✅' if langchain_installed else '❌'}")
    logger.info(f"Document processing requirements: {'✅' if doc_processing_installed else '❌'}")
    logger.info(f"Configuration files: ✅")
    logger.info(f"Sample document: ✅")
    logger.info("\nSetup completed!")
    
    # Next steps
    logger.info("\nNext steps:")
    logger.info("1. Copy .env.template to .env and add your API keys")
    logger.info("2. Start the API server: python enhanced_main.py")
    logger.info("3. Start the UI: streamlit run enhanced_streamlit_app.py")
    logger.info("4. Access the UI at http://localhost:8501")

if __name__ == "__main__":
    main()
