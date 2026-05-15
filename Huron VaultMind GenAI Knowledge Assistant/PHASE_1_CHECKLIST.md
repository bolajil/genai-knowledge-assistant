# Phase 1: Repo Stabilization — Detailed Checklist
**Timeline:** Week 1 (Days 1-5)  
**Priority:** CRITICAL — Do First

---

## Day 1: Critical Fixes

### ☐ Fix `.env.example` Merge Conflict (IMMEDIATE)
**File:** `.env.example` (lines 75-84)

**Current state:**
```
<<<<<<< HEAD

# --- Web Search Configuration ---
# Bing Web Search API (Recommended for production)
BING_SEARCH_API_KEY=your_bing_search_api_key_here

# Note: DuckDuckGo search works automatically if duckduckgo-search package is installed
# Install with: pip install duckduckgo-search
=======
>>>>>>> clean-master
```

**Action:** Remove conflict markers, keep the web search config section

**Verify:** `git diff --check` passes with no conflict markers

---

### ☐ Update `.gitignore` 

Add these patterns:
```
/data/
/indexes/
*.faiss
*.pkl
/archive_cleanup_*/
/archive_conflict_backups/
/mcp_logs.db
```

---

## Day 2: Root Directory Cleanup

### ☐ Files to KEEP at Root (4-5 files only)
- [ ] `README.md` — Rewrite for Huron reviewer
- [ ] `DEPLOYMENT.md` — Keep
- [ ] `requirements.txt` — Consolidated (merge from 10 files)
- [ ] `.env.example` — After fixing conflicts
- [ ] `CHANGELOG.md` — Create new

### ☐ Files to MOVE to `docs/`

| File | Destination |
|------|-------------|
| `AGENT_SEARCH_INTEGRATION.md` | `docs/integration/` |
| `AUTHENTICATION_TROUBLESHOOTING.md` | `docs/troubleshooting/` |
| `AUTOMATION_ROADMAP.md` | `docs/roadmap/` |
| `CHAT_ASSISTANT_SETUP.md` | `docs/setup/` |
| `COMPLETE_TAB_GUIDE.md` | `docs/guides/` |
| `DEMO_GUIDE.md` | `docs/guides/` |
| `DEPLOYMENT_GUIDE.md` | `docs/deployment/` |
| `DOCKER_QUICKSTART.md` | `docs/setup/` |
| `DOCUMENTATION_INDEX.md` | `docs/` (root index) |
| `DOCUMENT_ASSISTANT.md` | `docs/features/` |
| `DOCUMENT_QUALITY_GUIDE.md` | `docs/guides/` |
| `ENTERPRISE_DEPLOYMENT.md` | `docs/deployment/` |
| `ENTERPRISE_FEATURES_GUIDE.md` | `docs/features/` |
| `HEALTH_CHECK_GUIDE.md` | `docs/operations/` |
| `HYBRID_SETUP_GUIDE.md` | `docs/setup/` |
| `INDUSTRY_APPLICATIONS.md` | `docs/business/` |
| `INGESTION_TAB_REVIEW.md` | `docs/reviews/` |
| `INSTALL_MONITORING.md` | `docs/setup/` |
| `INSTALL_TESSERACT.md` | `docs/setup/` |
| `LOGO_SETUP.md` | `docs/setup/` |
| `MCP_SYSTEM_README.md` | `docs/architecture/` |
| `ML_MODELS_README.md` | `docs/architecture/` |
| `NOTIFICATION_TAB_READY.md` | `docs/features/` |
| `PRODUCTION_DEPLOYMENT_GUIDE.md` | `docs/deployment/` |
| `PUBLISH_CHECKLIST.md` | `docs/operations/` |
| `PUSH_NOTIFICATION_SETUP.md` | `docs/setup/` |
| `PUSH_TO_GITHUB_GUIDE.md` | `docs/operations/` |
| `QUALITY_CHECKER_*.md` | `docs/features/` |
| `QUERY_*.md` | `docs/features/` |
| `README_*.md` | `docs/guides/` |
| `SECURITY_CONFIGURATION.md` | `docs/security/` |
| `START_HERE.md` | `docs/` (getting started) |
| `TESTING_GUIDE.md` | `docs/testing/` |
| `TEST_README.md` | `docs/testing/` |
| `TODO.md` | `docs/roadmap/` |
| `VaultMind_Tab_Documentation.md` | `docs/features/` |
| `WEAVIATE_*.md` | `docs/setup/` |
| `WEB_*.md` | `docs/setup/` |

### ☐ Files to DELETE (one-time scripts, not needed)
- [ ] `GITHUB_PUSH_INSTRUCTIONS.md` (empty file - 0 bytes)
- [ ] `setup_guide.md` (empty file - 0 bytes)
- [ ] `test_query_tab.bat` (empty file - 0 bytes)
- [ ] Batch files that are one-time operations

---

## Day 3: Utils Deduplication

### ☐ *_updated.py Files to Resolve

| File | Supersedes | Action |
|------|------------|--------|
| `unified_content_generator_updated.py` (8KB) | `unified_content_generator.py` (15KB) | Compare, keep larger? |
| `unified_search_engine_updated.py` (6KB) | `unified_search_engine.py` (33KB) | Compare, keep larger? |

**Note:** The "updated" versions are smaller — may be refactored. Need to trace imports before deciding.

### ☐ Enterprise Files to KEEP (needed for Huron)
- `enterprise_caching_system.py`
- `enterprise_document_processor.py`
- `enterprise_hybrid_search.py`
- `enterprise_integration_layer.py`
- `enterprise_llm_enhancer.py`
- `enterprise_metadata_filtering.py`
- `enterprise_response_formatter.py`
- `enterprise_search_engine.py`
- `enterprise_semantic_chunking.py`
- `enterprise_structured_output.py`

### ☐ Files to Audit for Consolidation

**Search/Retrieval consolidation:**
- `direct_vector_search.py`
- `enhanced_search.py`
- `enhanced_retrieval.py`
- `enhanced_hybrid_retrieval.py`
- `unified_search_engine.py`
- `simple_search.py`
- `multi_source_search.py`
- `new_multi_source_search.py`
→ Target: 2-3 canonical search implementations

**Document processing consolidation:**
- `enhanced_document_processor.py`
- `enterprise_document_processor.py`
- `intelligent_content_extractor.py`
- `robust_pdf_extractor.py`
→ Target: 1-2 canonical processors

---

## Day 4: Tabs Deduplication

### ☐ Document Ingestion (3 → 1)
| File | Size | Keep? |
|------|------|-------|
| `document_ingestion.py` | 34KB | Merge features |
| `document_ingestion_fixed.py` | 70KB | Contains fixes |
| `document_ingestion_weaviate.py` | 15KB | Weaviate-specific |

**Recommendation:** Merge `document_ingestion_fixed.py` + weaviate features → single `document_ingestion.py`

### ☐ Enhanced Research (3 → 1)
| File | Size | Keep? |
|------|------|-------|
| `enhanced_research.py` | 30KB | Original |
| `enhanced_research_optimized.py` | 36KB | Optimized |
| `enhanced_research_updated.py` | 13KB | Smaller? |

**Recommendation:** Keep `enhanced_research_optimized.py`, rename to `enhanced_research.py`

### ☐ Multi-Content Dashboard (3 → 1)
| File | Size | Keep? |
|------|------|-------|
| `multi_content_dashboard.py` | 16KB | Original |
| `multi_content_dashboard_enhanced.py` | 12KB | Smaller |
| `multi_content_enhanced.py` | 190KB | Full featured |

**Recommendation:** Keep `multi_content_enhanced.py`

### ☐ Agent Assistant (2 → 1)
| File | Size | Keep? |
|------|------|-------|
| `agent_assistant.py` | 19KB | Standard |
| `agent_assistant_hybrid.py` | 13KB | Hybrid features |

**Recommendation:** Merge hybrid features into main

---

## Day 5: API and Requirements Consolidation

### ☐ API Files (5 → 3)
| Current | Action |
|---------|--------|
| `ingest_api.py` (776 bytes) | Delete (stub) |
| `enhanced_ingest_api.py` (11KB) | Rename to `ingest_api.py` |
| `query_api.py` (753 bytes) | Delete (stub) |
| `enhanced_query_api.py` (7KB) | Rename to `query_api.py` |
| `agent_server.py` (631 bytes) | Keep |

### ☐ Requirements Files (10 → 2)

**Merge into `requirements.txt`:**
```
# Core Dependencies
...contents of requirements.txt...

# Authentication
...contents of requirements-auth.txt...

# Enterprise Features
...contents of requirements-enterprise.txt...

# Vector Stores
...contents of requirements-weaviate.txt...
...contents of requirements-multi-vector.txt...

# Automation
...contents of requirements-automation.txt...

# Multi-Content
...contents of requirements-multicontent.txt...
```

**Keep separate:**
- `requirements-ml-models.txt` — Heavy optional dependencies

---

## Exit Criteria Checklist

- [ ] Root has ≤6 files (README, CHANGELOG, CONTRIBUTING, DEPLOYMENT, requirements.txt, .env.example)
- [ ] `git diff --check` passes (no conflict markers)
- [ ] `utils/` reduced to ≤60 files
- [ ] `tabs/` has 1 canonical file per feature
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `git log --all -- archive_cleanup_*` returns empty (history purged)
- [ ] All imports updated to canonical file names

---

## Commands Reference

```bash
# Move markdown files to docs
git mv AGENT_SEARCH_INTEGRATION.md docs/integration/

# Check for merge conflicts
git diff --check

# Purge archive folders from history (DANGEROUS - backup first!)
git filter-repo --path archive_cleanup_20250919_082734 --invert-paths

# Find all imports of a file
grep -r "from utils.unified_search_engine" .
grep -r "import unified_search_engine" .
```

---

**Next:** After Phase 1 complete, proceed to Phase 2 (Multi-Tenant Foundation)
