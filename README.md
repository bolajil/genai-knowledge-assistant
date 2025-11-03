# VaultMind GenAI Knowledge Assistant

Enterprise-grade AI assistant for finding trusted answers across your organization’s documents, spreadsheets, BI dashboards, and structured data — with citations and permissions built in.

## Overview (TL;DR)
- What it is: An enterprise knowledge assistant that retrieves and synthesizes answers with citations from your documents and data.
- Why it matters: Cuts search time, improves trust via citations, and respects permissions and roles.
- How it works: Ingest + chunk + embed; hybrid retrieval (BM25 + vectors with re‑ranking); optional LLM synthesis; robust fallbacks and logging.

Quick links
- Demo repo (Streamlit, Demo Mode)
- Live demo URL: configure via Streamlit Community Cloud (Main file: `app.py`, Python 3.10)https://genai-knowledge-assistant-8gmzhaf3k4wduueal3u4ks.streamlit.app/
- Request a User login and Password from this email: bolafiz2001@gmail.com
- ICP (Ideal Customer Profile): see [docs/ICP.md](docs/ICP.md)
- One‑pager / Deck: coming soon (docs/)

---

## Why VaultMind
Teams waste hours digging through SharePoint, Confluence, PDFs, Excel, and BI dashboards. VaultMind unifies retrieval with hybrid search (vector + keyword + re‑ranking), enforces enterprise permissions, and generates cited answers so users trust results and admins stay in control.

- Trustworthy: Retrieval-grounded responses with citations and structured outputs
- Enterprise-ready: Role‑based permissions, approval workflows, robust fallbacks
- Flexible: Works with Weaviate (cloud) and FAISS (local) — multi‑vector adapters available

---

## Who is this for
For a detailed, enterprise-ready Ideal Customer Profile see [docs/ICP.md](docs/ICP.md).

- Legal & Compliance teams — retrieve policies, ByLaws, audit trails
- Operations / Policy teams — streamline SOP access, reduce escalations
- Customer Support & RevOps — surface accurate answers with citations
- Platform & AI leads — pilot GenAI internally, evaluate enterprise readiness

---

## Key Features
- Hybrid search with re‑ranking
  - BM25 + vector similarity + cross‑encoder re‑ranking
  - Source: `utils/enterprise_hybrid_search.py`
- Unified retrieval across tabs
  - Consistent document search used by Chat, Query, and Agent assistants
  - Source: `utils/unified_document_retrieval.py`
- Enhanced LLM integration
  - Structure‑aware chunking, context building, validation, and citations
  - Source: `utils/enhanced_llm_integration.py`, `utils/enterprise_semantic_chunking.py`
- Weaviate + FAISS support (with migration tooling)
  - Cloud Weaviate (GCP‑friendly prefix discovery) and local FAISS fallback
  - Sources: `utils/weaviate_manager.py`, `utils/faiss_to_weaviate_migrator.py`
- Enterprise permissions + approvals
  - Role‑based access, request/approval workflow, analytics
  - Sources: `app/auth/enterprise_permissions.py`, `app/auth/resource_request_manager.py`
- Multi‑Content Dashboard (PowerBI + Excel + multi‑source search)
  - Source: `tabs/multi_content_enhanced.py`
- Enhanced Agent Assistant (document‑aware with source attribution)
  - Source: `tabs/agent_assistant_enhanced.py`
- Multi‑vector storage architecture (adapters & manager)
  - Adapters for OpenSearch, Azure AI Search, Vertex AI, Pinecone, Qdrant, PGVector, Weaviate, FAISS (MongoDB WIP)
  - Sources: `utils/multi_vector_storage_interface.py`, `utils/adapters/`

---

## Quickstart (Local)
Prerequisites
- Python 3.10+ (recommended)
- Windows/macOS/Linux

1) Clone and set env
```
git clone <your_fork_or_repo_url>
cd genai-knowledge-assistant
copy .env.example .env.local   # on Windows (or: cp .env.example .env.local)
```

2) Install dependencies
```
pip install -r cloud_requirements.txt
```

3) Run the app (Streamlit)
```
streamlit run enhanced_streamlit_app.py
```

4) Optional: CLI & diagnostics
```
python scripts/diagnostics/diagnose_weaviate_query.py
python scripts/weaviate_schema_audit.py
python scripts/ingest/ingest_csv.py --help
```

Notes
- If you don’t have Weaviate set up, the system falls back to FAISS where possible.
- For email features in Agent Assistant, configure SMTP or Microsoft Graph in the UI or via `.env.local`.

---

## Demo Mode
Demo Mode is implemented for a one‑click experience with a bundled FAISS index and no external calls.
- Toggle via env: `DEMO_MODE=true`
- Default to FAISS, disable outbound web/API calls in demo
- Preloaded sample index from `template/index_data/test_index/`

You can host a live instance on Streamlit Community Cloud and/or mirror it on Hugging Face Spaces. Links will appear here after deployment.

Quick test locally (PowerShell):
```
$env:DEMO_MODE='true'; streamlit run enhanced_streamlit_app.py
```

---

## Architecture (high‑level)
- UI: Streamlit tabs (Chat, Query, Agent, Multi‑Content)
- Retrieval: Unified retrieval + hybrid search + re‑ranking
- Vector DB: Weaviate (cloud) and FAISS (local) with fallback; multi‑vector adapters
- LLM: Enhanced integration for context building, chunking, structured outputs
- Security: RBAC, approvals, resource request flows

Key files (high‑signal, non‑exhaustive)
- `utils/enterprise_hybrid_search.py` — hybrid search with re‑ranking
- `utils/unified_document_retrieval.py` — central retrieval API
- `utils/weaviate_manager.py` — robust Weaviate management (GCP‑friendly)
- `utils/faiss_to_weaviate_migrator.py` — migration utility
- `utils/enhanced_llm_integration.py` — structured LLM processing
- `app/auth/enterprise_permissions.py` — RBAC
- `app/auth/resource_request_manager.py` — permission request workflow
- `tabs/agent_assistant_enhanced.py`, `tabs/multi_content_enhanced.py`

---

## Security & Permissions
- Role‑based access (RBAC) with feature‑level controls
- Admin approval workflows for elevated features
- Demo Mode disables outbound calls for safer public testing

See also: `SECURITY_CONFIGURATION.md` (coming soon) and `docs/ICP.md` for target org profiles.

---

## Roadmap (selected)
- Demo Mode (bundled FAISS index + hosted preview)
- Connectors: SharePoint, Confluence, Google Drive, Slack, Jira
- SSO/IdP integrations (Azure AD/Entra, Okta)
- Audit logs, analytics dashboard, admin console
- Product Hunt / HN launch

---

## Contributing
Issues and PRs are welcome. Please open an issue for feature requests or bugs.

Planned repo hygiene
- Add LICENSE (MIT) and issue templates
- Add docs/ with architecture diagram and one‑pager/pitch deck

---

## License
TBD (MIT planned) — will be added to the repository root.
