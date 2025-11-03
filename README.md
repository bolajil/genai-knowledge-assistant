# VaultMind GenAI Knowledge Assistant

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/langchain-0.1+-yellow.svg)](https://langchain.com)
[![LangGraph](https://img.shields.io/badge/langgraph-0.6+-orange.svg)](https://langchain-ai.github.io/langgraph/)

**Enterprise RAG with multi-vector search, hybrid retrieval, LangGraph autonomous reasoning, and intelligent document quality control**

<<<<<<< HEAD
[🎬 Live Demo](#demo) | [📖 Documentation](#documentation) | [🚀 Quick Start](#quickstart-local) | [💡 Features](#key-features)

---

## Overview

VaultMind is an enterprise-grade GenAI knowledge assistant that turns scattered documents and analytics into trustworthy, cited answers. It intelligently routes queries between fast retrieval and deep reasoning, ensuring optimal performance for every question.

### What Makes VaultMind Different

✨ **Hybrid Intelligence** - Automatically routes simple queries to fast retrieval, complex queries to LangGraph autonomous agent  
🎯 **Multi-Vector Flexibility** - Works with Weaviate, FAISS, OpenSearch, Azure AI Search, Vertex AI, Pinecone, Qdrant, PGVector  
📊 **Document Quality Control** - Automatically detects and fixes OCR errors, missing spaces, and text quality issues  
🔒 **Enterprise-Ready** - RBAC, audit logs, approval workflows, and compliance-ready governance  
🤖 **BYO-LLM** - OpenAI, Anthropic, Mistral, Groq, Ollama - no vendor lock-in  
📈 **Production-Tested** - Handles 1000+ documents, real-time ingestion, comprehensive monitoring

### Quick Links
- 📚 [Demo Guide](DEMO_GUIDE.md) - Complete demo scenarios and talk tracks
- 🚀 [Deployment Guide](DEPLOYMENT.md) - Local, Docker, Cloud deployment options
- ✅ [Publishing Checklist](PUBLISH_CHECKLIST.md) - Go-to-market preparation
- ⚡ [Quick Publish](QUICK_PUBLISH.md) - Deploy in 30 minutes
- 📊 [Document Quality Guide](DOCUMENT_QUALITY_GUIDE.md) - Fix OCR and text issues
=======
Quick links
- Demo repo (Streamlit, Demo Mode)
- Live demo URL: configure via Streamlit Community Cloud (Main file: `app.py`, Python 3.10)https://genai-knowledge-assistant-8gmzhaf3k4wduueal3u4ks.streamlit.app/
- Request a User login and Password from this email: bolafiz2001@gmail.com
- ICP (Ideal Customer Profile): see [docs/ICP.md](docs/ICP.md)
- One‑pager / Deck: coming soon (docs/)
>>>>>>> de525cfb8f3a30a0114d9c873e8c05ffaf697075

---

## Why VaultMind
Teams waste hours digging through SharePoint, Confluence, PDFs, Excel, and BI dashboards. VaultMind unifies retrieval with hybrid search (vector + keyword + re‑ranking), enforces enterprise permissions, and generates cited answers so users trust results and admins stay in control.

---

## Key Features

### 🧠 Hybrid LangGraph Intelligence (NEW)
- **Query Complexity Analysis** - Automatically classifies queries as simple/moderate/complex/very complex
- **Intelligent Routing** - Fast retrieval for simple queries, LangGraph reasoning for complex ones
- **Autonomous Agent** - Multi-step reasoning, tool usage, cross-document analysis
- **Performance Tracking** - Real-time metrics on routing decisions and response times
- **Sources:** `utils/query_complexity_analyzer.py`, `utils/hybrid_query_orchestrator.py`, `app/utils/langgraph_agent.py`, `tabs/agent_assistant_hybrid.py`

### 📊 Document Quality Control (NEW)
- **Automatic Quality Detection** - Identifies missing spaces, OCR errors, concatenated words
- **Interactive Cleaning** - Preview before/after, standard and aggressive modes
- **Quality Scoring** - 0-1 scale with actionable recommendations
- **Batch Processing** - Check multiple documents simultaneously
- **Sources:** `utils/document_quality_checker.py`, `utils/document_quality_ui.py`

### 🔍 Hybrid Search & Re-Ranking
- **Multi-Signal Search** - BM25 keyword + vector similarity + cross-encoder re-ranking
- **Confidence Thresholding** - Eliminates irrelevant results automatically
- **Query Enhancement** - Expands queries with synonyms and domain knowledge
- **Source:** `utils/enterprise_hybrid_search.py`, `utils/query_enhancement.py`

### 🗄️ Multi-Vector Storage
- **Cloud & Local** - Weaviate (cloud), FAISS (local), or both
- **Enterprise Adapters** - OpenSearch, Azure AI Search, Vertex AI, Pinecone, Qdrant, PGVector
- **Migration Tools** - Seamless FAISS ↔ Weaviate migration
- **Sources:** `utils/multi_vector_storage_interface.py`, `utils/weaviate_manager.py`, `utils/faiss_to_weaviate_migrator.py`

### 🤖 Enhanced LLM Integration
- **Multi-Provider Support** - OpenAI, Anthropic, Mistral, Groq, Ollama
- **Structured Outputs** - Executive summaries, analysis, citations, key points
- **Context Building** - Intelligent chunking (1500/500) with metadata preservation
- **Fallback Chains** - Automatic provider switching for reliability
- **Sources:** `utils/enhanced_llm_integration.py`, `utils/llm_config.py`

### 🔒 Enterprise Security & Governance
- **RBAC** - Role-based access control with feature-level permissions
- **Approval Workflows** - Request/approval system for elevated access
- **Audit Logs** - Comprehensive activity tracking
- **MFA Support** - Two-factor authentication with TOTP
- **Sources:** `app/auth/enterprise_permissions.py`, `app/auth/resource_request_manager.py`

### 📈 Multi-Content Dashboard
- **PowerBI Integration** - Embedded reports with Azure AD auth
- **Excel Analytics** - Multi-sheet viewer with interactive charts
- **Multi-Source Search** - Unified search across documents, BI, web
- **Source:** `tabs/multi_content_enhanced.py`

### 📊 Analytics & Monitoring
- **Performance Metrics** - Query times, routing decisions, success rates
- **User Feedback System** - Thumbs up/down with detailed feedback forms
- **Health Dashboards** - Vector store status, LLM availability, system health
- **Export Capabilities** - CSV, JSON export for analysis
- **Sources:** `utils/user_feedback_system.py`, `tabs/feedback_analytics_tab.py`

---

## Quickstart (Local)

### Prerequisites
- Python 3.9-3.11 (recommended: 3.11)
- Windows/macOS/Linux
- Git (for cloning)
- OpenAI API key (or other LLM provider)

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/vaultmind-genai-assistant
cd vaultmind-genai-assistant

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-complete.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your API keys:
# OPENAI_API_KEY=sk-...
# WEAVIATE_URL=https://... (optional)
# WEAVIATE_API_KEY=... (optional)

# 5. Run the application
streamlit run genai_dashboard_modular.py
```

### First-Time Setup

1. **Access the app:** http://localhost:8501
2. **Login:** Use default credentials or create new user
3. **Ingest a document:**
   - Go to "📄 Ingest Document" tab
   - Upload a PDF or text file
   - Wait for processing (automatic quality check included)
4. **Test queries:**
   - **Simple:** Go to "🔍 Query Assistant" - fast retrieval
   - **Complex:** Go to "🧠 Agent (Hybrid)" - LangGraph reasoning

### Verify Installation

```bash
# Run pre-flight check
python scripts/demo_preflight_check.py

# Should show:
# [PASS] Python Version
# [PASS] All dependencies installed
# [PASS] Configuration ready
# [SUCCESS] VaultMind is ready for demo!
```

### Quick Test

```bash
# Check indexes
python check_indexes.py

# Check configuration
python check_config.py

# Test document quality checker
python -c "from utils.document_quality_checker import check_document_quality; print('✅ Quality checker ready!')"
```

---

## Demo Mode
Demo Mode is implemented for a one‑click experience with a bundled FAISS index and no external calls.
Toggle via env: `DEMO_MODE=true`
Default to FAISS, disable outbound web/API calls in demo
Preloaded sample index from `template/index_data/test_index/`
- Toggle via env: `DEMO_MODE=true`
- Default to FAISS, disable outbound web/API calls in demo
- Preloaded sample index from `template/index_data/test_index/`

You can host a live instance on Streamlit Community Cloud and/or mirror it on Hugging Face Spaces. Links will appear here after deployment.

Quick test locally (PowerShell):
```
$env:DEMO_MODE='true'; streamlit run enhanced_streamlit_app.py
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                        │
│  Query │ Chat │ Agent │ Hybrid Agent │ Multi-Content │ Admin │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Hybrid Query Orchestrator (NEW)                 │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │ Complexity       │  →  →   │ Fast Retrieval          │  │
│  │ Analyzer         │         │ (Simple queries)        │  │
│  └──────────────────┘         └─────────────────────────┘  │
│           ↓                                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ LangGraph Agent (Complex queries)                     │  │
│  │ • Multi-step reasoning • Tool usage • Synthesis      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Retrieval & Processing                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Document     │  │ Hybrid       │  │ Query           │  │
│  │ Quality      │→ │ Search       │→ │ Enhancement     │  │
│  │ Checker (NEW)│  │ + Re-ranking │  │ & Expansion     │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Vector Storage Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Weaviate │  │  FAISS   │  │OpenSearch│  │ Pinecone  │  │
│  │ (Cloud)  │  │ (Local)  │  │ Azure AI │  │  Qdrant   │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      LLM Integration                         │
│  OpenAI │ Anthropic │ Mistral │ Groq │ Ollama (Local)      │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**Ingestion Pipeline:**
1. Document upload (PDF, TXT, DOCX, Excel)
2. Quality analysis and cleaning (NEW)
3. Text extraction (pdfplumber, pymupdf, PyPDF2)
4. Semantic chunking (1500/500 with overlap)
5. Embedding generation (sentence-transformers)
6. Vector storage (Weaviate/FAISS/multi-cloud)

**Query Pipeline:**
1. Query complexity analysis (NEW)
2. Intelligent routing (fast vs LangGraph)
3. Query enhancement and expansion
4. Hybrid search (BM25 + vector + re-ranking)
5. LLM synthesis with citations
6. Structured response formatting

**Core Files:**

**NEW - Hybrid Intelligence:**
- `utils/query_complexity_analyzer.py` - Query classification
- `utils/hybrid_query_orchestrator.py` - Intelligent routing
- `app/utils/langgraph_agent.py` - Autonomous agent
- `tabs/agent_assistant_hybrid.py` - Hybrid UI

**NEW - Document Quality:**
- `utils/document_quality_checker.py` - Quality analysis
- `utils/document_quality_ui.py` - Cleaning UI

**Retrieval & Search:**
- `utils/enterprise_hybrid_search.py` - Hybrid search
- `utils/query_enhancement.py` - Query expansion
- `utils/advanced_reranker.py` - Result re-ranking
- `utils/unified_document_retrieval.py` - Unified API

**Vector Storage:**
- `utils/weaviate_manager.py` - Weaviate integration
- `utils/multi_vector_storage_interface.py` - Multi-cloud adapters
- `utils/faiss_to_weaviate_migrator.py` - Migration tools

**LLM Integration:**
- `utils/enhanced_llm_integration.py` - LLM processing
- `utils/llm_config.py` - Multi-provider config
- `utils/enterprise_structured_output.py` - Response formatting

**Security & Auth:**
- `app/auth/enterprise_permissions.py` - RBAC
- `app/auth/resource_request_manager.py` - Approvals
- `app/auth/mfa_manager.py` - Two-factor auth

---

## Security & Permissions
- Role‑based access (RBAC) with feature‑level controls
- Admin approval workflows for elevated features
- Demo Mode disables outbound calls for safer public testing

See also: `SECURITY_CONFIGURATION.md` (coming soon) and `docs/ICP.md` for target org profiles.

---

## What's New

### v2.0 (Current) - Hybrid Intelligence Release

✅ **Hybrid LangGraph System**
- Automatic query complexity analysis
- Intelligent routing between fast and deep reasoning
- LangGraph autonomous agent for complex queries
- Real-time performance metrics

✅ **Document Quality Control**
- Automatic OCR error detection
- Interactive cleaning with preview
- Quality scoring and recommendations
- Batch processing support

✅ **Publication Ready**
- Complete demo guide with talk tracks
- Deployment documentation (local, Docker, cloud)
- Publishing checklist and 30-minute quick start
- Pre-flight validation scripts

### v1.5 - Enterprise Features
- Multi-vector storage adapters (9 providers)
- Enhanced query system with feedback
- PowerBI and Excel integration
- Advanced permissions and RBAC

### v1.0 - Foundation
- Weaviate and FAISS support
- Hybrid search with re-ranking
- Enterprise LLM integration
- Basic permissions system

## Roadmap

### Q1 2026
- [ ] Advanced LangGraph workflows
- [ ] Custom quality rules per document type
- [ ] Real-time collaboration features
- [ ] Enhanced analytics dashboard

### Q2 2026
- [ ] SharePoint, Confluence, Google Drive connectors
- [ ] SSO/IdP integrations (Azure AD, Okta)
- [ ] Advanced audit logging
- [ ] Mobile-responsive UI

### Future
- [ ] Multi-language support
- [ ] Voice query interface
- [ ] Advanced visualization tools
- [ ] Custom LLM fine-tuning

---

## Documentation

### User Guides
- [📚 Demo Guide](DEMO_GUIDE.md) - Complete demo scenarios (5min, 25min, custom)
- [📊 Document Quality Guide](DOCUMENT_QUALITY_GUIDE.md) - Fix OCR and text issues
- [🔧 Hybrid Setup Guide](HYBRID_SETUP_GUIDE.md) - Configure hybrid system

### Deployment
- [🚀 Deployment Guide](DEPLOYMENT.md) - All deployment options
- [⚡ Quick Publish](QUICK_PUBLISH.md) - Deploy in 30 minutes
- [✅ Publishing Checklist](PUBLISH_CHECKLIST.md) - Go-to-market prep

### Development
- [🏗️ Architecture](docs/architecture.md) - System design (coming soon)
- [🔌 API Reference](docs/api.md) - Integration guide (coming soon)
- [🧪 Testing Guide](docs/testing.md) - Test suite (coming soon)

## Support & Community

### Getting Help
- 📖 **Documentation:** Check guides above
- 🐛 **Issues:** [GitHub Issues](https://github.com/yourusername/vaultmind/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/yourusername/vaultmind/discussions)
- 📧 **Email:** support@vaultmind.ai

### Contributing

We welcome contributions! Here's how:

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Make your changes** and test thoroughly
4. **Commit:** `git commit -m 'Add amazing feature'`
5. **Push:** `git push origin feature/amazing-feature`
6. **Open a Pull Request**

**Contribution Guidelines:**
- Follow existing code style
- Add tests for new features
- Update documentation
- Keep PRs focused and atomic

### Code of Conduct

Be respectful, inclusive, and professional. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 VaultMind

## Acknowledgments

**Built with:**
- [Streamlit](https://streamlit.io) - UI framework
- [LangChain](https://langchain.com) - LLM orchestration
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent framework
- [Weaviate](https://weaviate.io) - Vector database
- [FAISS](https://github.com/facebookresearch/faiss) - Local vector search
- [Sentence Transformers](https://www.sbert.net) - Embeddings

**Special thanks to:**
- The open-source community
- Early adopters and testers
- Contributors and supporters

---

**Ready to transform your knowledge management?**

[🚀 Get Started](#quickstart-local) | [📖 Read the Docs](#documentation) | [💬 Join Community](#support--community)

---

<p align="center">Made with ❤️ for teams who value knowledge</p>
