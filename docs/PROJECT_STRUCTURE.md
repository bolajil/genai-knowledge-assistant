# VaultMind GenAI Knowledge Assistant - Project Structure

## Core Application Files

### Main Entry Points
- `genai_dashboard_modular.py` - Main Streamlit dashboard (recommended)
- `genai_dashboard.py` - Full-featured dashboard 
- `genai_dashboard_secure.py` - Enterprise secure dashboard
- `main.py` - Alternative entry point

### Batch Scripts
- `run_app.bat` - Start the application
- `start_vaultmind.bat` - Quick start script
- `run_vaultmind.bat` - Enhanced start script

## Directory Structure

### `/app/` - Core Application Logic
- `/agents/` - AI agent implementations
- `/auth/` - Authentication and authorization
- `/mcp/` - MCP (Model Context Protocol) integration
- `/middleware/` - Request/response middleware

### `/api/` - API Endpoints
- `agent_server.py` - Agent API server
- `ingest_api.py` - Document ingestion API
- `query_api.py` - Query processing API

### `/tabs/` - Streamlit Tab Components
- `query_assistant.py` - Document query interface
- `agent_assistant_enhanced.py` - Enhanced AI assistant
- `admin_panel.py` - Administration interface
- And 17+ other specialized tabs

### `/utils/` - Utility Functions
- `comprehensive_document_retrieval.py` - Document search
- `enhanced_llm_integration.py` - LLM processing
- `vector_search_with_embeddings.py` - Vector search engine
- `embedding_generator.py` - Embedding generation
- And 59+ other utility modules

### `/config/` - Configuration Files
- `agent_config.py` - Agent configuration
- `dashboard_config.py` - Dashboard settings
- `enterprise_config.py` - Enterprise features
- `/environments/` - Environment-specific configs

### `/data/` - Data Storage
- `/indexes/` - Document indexes
- `/faiss_index/` - Vector database files
- `/uploads/` - Uploaded documents
- `/backups/` - Index backups

### `/scripts/` - Utility Scripts
- `/ingest/` - Document ingestion scripts
- `cleanup_project_files.py` - Project maintenance
- And 14+ other utility scripts

### `/tests/` - Test Suite
- `test_agent_integration.py` - Agent testing
- `test_agent_search.py` - Search testing
- `test_embeddings.py` - Embedding testing

### `/ui/` - UI Components
- `enhanced_research_ui.py` - Research interface
- `ingest_any_ui.py` - Document ingestion UI
- And 8+ other UI modules

### `/mcp/` - MCP System
- `integration.py` - MCP integration layer
- `logger.py` - MCP logging
- `/tools/` - MCP tools and utilities

## Configuration Files

### Requirements
- `requirements.txt` - Core dependencies
- `requirements-enterprise.txt` - Enterprise features
- `requirements-auth.txt` - Authentication
- `requirements-weaviate.txt` - Weaviate integration

### Environment
- `.env.example` - Environment template
- `.env` - Local environment variables
- `constraints.txt` - Dependency constraints

### Docker
- `Dockerfile.production` - Production container
- `.dockerignore` - Docker ignore patterns
- `flowise.yml` - Flowise configuration

## Documentation

### Setup & Deployment
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `PRODUCTION_DEPLOYMENT_GUIDE.md` - Production setup
- `DOCKER_QUICKSTART.md` - Docker setup
- `ENTERPRISE_DEPLOYMENT.md` - Enterprise deployment

### Feature Guides
- `ENTERPRISE_FEATURES_GUIDE.md` - Enterprise capabilities
- `WEAVIATE_SETUP_GUIDE.md` - Weaviate integration
- `AUTHENTICATION_TROUBLESHOOTING.md` - Auth issues
- `SECURITY_CONFIGURATION.md` - Security setup

### Technical Documentation
- `VaultMind_Tab_Documentation.md` - Tab system overview
- `MCP_SYSTEM_README.md` - MCP system details
- `VECTOR_DB_FIX_README.md` - Vector DB troubleshooting
- `SYSTEM_STATUS_SUMMARY.md` - System status overview

## Key Features

### Document Processing
- Multi-format document ingestion (PDF, TXT, DOCX)
- Intelligent text extraction and chunking
- Vector embedding generation using sentence-transformers
- FAISS-based vector search with semantic similarity

### AI Integration
- Multiple LLM provider support (OpenAI, local models)
- Enhanced prompt engineering and context building
- Quality validation and response scoring
- Fallback mechanisms for reliability

### Enterprise Features
- Active Directory authentication integration
- Role-based access control
- Audit logging and compliance tracking
- Multi-tenant support with data isolation

### Vector Database Support
- FAISS for high-performance vector search
- Weaviate integration for cloud-native deployment
- Automatic embedding generation and indexing
- Hybrid search combining keyword and semantic matching

### User Interface
- Modular Streamlit-based dashboard
- Multiple specialized interfaces for different use cases
- Real-time query processing and response streaming
- Interactive document exploration and analysis

This structure supports enterprise-grade document analysis and AI-powered knowledge assistance with robust security, scalability, and maintainability.
