# Utils Directory Audit
**Current State:** 158 files  
**Target:** ~60 files  
**Reduction:** ~62%

---

## Category Analysis

### 🟢 KEEP — Enterprise Features (10 files)
These are critical for Huron enterprise deployment:

| File | Size | Purpose |
|------|------|---------|
| `enterprise_caching_system.py` | 17KB | Redis caching |
| `enterprise_document_processor.py` | 12KB | Doc processing |
| `enterprise_hybrid_search.py` | 15KB | Hybrid search |
| `enterprise_integration_layer.py` | 18KB | Integration |
| `enterprise_llm_enhancer.py` | 11KB | LLM enhancement |
| `enterprise_metadata_filtering.py` | 15KB | Metadata filters |
| `enterprise_response_formatter.py` | 12KB | Response formatting |
| `enterprise_search_engine.py` | 15KB | Search engine |
| `enterprise_semantic_chunking.py` | 19KB | Semantic chunking |
| `enterprise_structured_output.py` | 18KB | Structured output |

---

### 🟢 KEEP — Core Infrastructure (15 files)

| File | Size | Purpose |
|------|------|---------|
| `weaviate_manager.py` | 143KB | Vector DB management |
| `multi_vector_storage_manager.py` | 40KB | Multi-vector routing |
| `multi_vector_storage_interface.py` | 10KB | Storage interface |
| `llm_config.py` | 12KB | LLM configuration |
| `index_manager.py` | 16KB | Index management |
| `embedding_generator.py` | 14KB | Embeddings |
| `notification_manager.py` | 23KB | Notifications |
| `user_feedback_system.py` | 20KB | Feedback system |
| `query_cache.py` | 18KB | Query caching |
| `unified_vector_store.py` | 15KB | Vector store |
| `vector_db_provider.py` | 40KB | DB provider |
| `response_writer.py` | 19KB | Response writing |
| `text_cleaning.py` | 13KB | Text cleaning |
| `ingestion_queue.py` | 16KB | Ingestion queue |
| `ingestion_validator.py` | 15KB | Validation |

---

### 🟡 CONSOLIDATE — Search/Retrieval (reduce 12 → 3)

**Current files:**
| File | Size | Status |
|------|------|--------|
| `unified_search_engine.py` | 33KB | KEEP as canonical |
| `unified_search_engine_updated.py` | 6KB | MERGE or DELETE |
| `enhanced_search.py` | 19KB | MERGE into unified |
| `enhanced_retrieval.py` | 11KB | MERGE into unified |
| `enhanced_hybrid_retrieval.py` | 18KB | MERGE into enterprise |
| `simple_search.py` | 16KB | KEEP for fallback |
| `direct_vector_search.py` | 12KB | MERGE into unified |
| `multi_source_search.py` | 53KB | KEEP - multi-source |
| `new_multi_source_search.py` | 20KB | MERGE or DELETE |
| `multi_source_search_wrapper.py` | 6KB | KEEP as wrapper |
| `search_service.py` | 10KB | MERGE into unified |
| `real_time_retrieval.py` | 19KB | KEEP - real-time |

**Target:** 
- `unified_search_engine.py` — Main semantic search
- `multi_source_search.py` — Multi-source search
- `simple_search.py` — Fallback search

---

### 🟡 CONSOLIDATE — Document Processing (reduce 8 → 2)

**Current files:**
| File | Size | Status |
|------|------|--------|
| `enhanced_document_processor.py` | 22KB | KEEP as canonical |
| `enterprise_document_processor.py` | 12KB | MERGE enterprise features |
| `intelligent_content_extractor.py` | 16KB | MERGE into processor |
| `robust_pdf_extractor.py` | 7KB | MERGE into processor |
| `pdf_section_extractor.py` | 8KB | MERGE into processor |
| `image_text_extractor.py` | 12KB | KEEP separate - OCR |
| `image_llm_query.py` | 16KB | KEEP separate - image LLM |
| `document_summary_generator.py` | 9KB | MERGE into processor |

**Target:**
- `document_processor.py` — Unified document processing
- `image_processor.py` — Image/OCR processing

---

### 🟡 CONSOLIDATE — Chunking Strategies (reduce 7 → 2)

**Current files:**
| File | Size | Status |
|------|------|--------|
| `advanced_chunking_strategy.py` | 18KB | KEEP as main |
| `semantic_chunking_strategy.py` | 15KB | MERGE |
| `enterprise_semantic_chunking.py` | 19KB | KEEP enterprise |
| `intelligent_chunking.py` | 14KB | MERGE |
| `improved_text_chunking.py` | 9KB | MERGE |
| `page_based_chunking.py` | 12KB | MERGE |
| `document_aware_chunking.py` | 18KB | MERGE |
| `enhanced_page_chunking.py` | 9KB | MERGE |
| `chunking_config.py` | 6KB | KEEP as config |

**Target:**
- `chunking_strategy.py` — Unified chunking
- `enterprise_semantic_chunking.py` — Enterprise features
- `chunking_config.py` — Configuration

---

### 🟡 CONSOLIDATE — Query Processing (reduce 6 → 2)

**Current files:**
| File | Size | Status |
|------|------|--------|
| `enhanced_query_processor.py` | 23KB | KEEP as main |
| `query_enhancement.py` | 16KB | MERGE |
| `query_expansion.py` | 8KB | MERGE |
| `query_complexity_analyzer.py` | 10KB | MERGE |
| `query_content_matcher.py` | 12KB | MERGE |
| `query_result_formatter.py` | 13KB | KEEP separate |
| `query_helpers.py` | 3KB | DELETE (minimal) |

**Target:**
- `query_processor.py` — Unified query processing
- `query_result_formatter.py` — Result formatting

---

### 🟡 CONSOLIDATE — Content Generation (reduce 4 → 1)

**Current files:**
| File | Size | Status |
|------|------|--------|
| `unified_content_generator.py` | 15KB | KEEP |
| `unified_content_generator_updated.py` | 8KB | DELETE |
| `custom_document_summary.py` | 13KB | MERGE |
| `bylaws_content_generator.py` | 6KB | DELETE (hardcoded) |

**Target:**
- `content_generator.py` — Unified generation

---

### 🔴 DELETE — Duplicate/Obsolete Files

| File | Reason |
|------|--------|
| `unified_content_generator_updated.py` | Duplicate |
| `unified_search_engine_updated.py` | Duplicate |
| `new_multi_source_search.py` | Likely duplicate |
| `direct_bylaws_retriever.py` | Hardcoded content |
| `bylaws_content_generator.py` | Hardcoded content |
| `direct_powers_retrieval.py` | Hardcoded content |
| `bylaw_query_patch.py` | Hardcoded content |
| `bylaw_retrieval.py` | Hardcoded content |
| `enhanced_llm_bylaw_patch.py` | Hardcoded content |
| `enhanced_search_bylaw_integration.py` | Hardcoded content |
| `demo_mode.py` | Development only |
| `mock_vector_db_provider.py` | Testing only (move to tests/) |
| `vector_db_provider_patch.py` | Patch file |

---

### 🟢 KEEP — Adapters Directory (12 files)

All adapters in `utils/adapters/` should be kept:
- `pinecone_adapter.py`
- `weaviate_adapter.py`
- `faiss_adapter.py`
- `azure_adapter.py`
- `opensearch_adapter.py`
- etc.

---

### 🟢 KEEP — Security Directory (4 files)

All files in `utils/security/` are needed:
- `rate_limiter.py`
- `input_validator.py`
- etc.

---

### 🟢 KEEP — Monitoring Directory (5 files)

All files in `utils/monitoring/` are needed for operations.

---

## Consolidation Priority

| Priority | Category | Current | Target | Effort |
|----------|----------|---------|--------|--------|
| 1 | Delete duplicates | 13 files | 0 | Low |
| 2 | Search/Retrieval | 12 files | 3 | Medium |
| 3 | Document Processing | 8 files | 2 | Medium |
| 4 | Chunking | 9 files | 3 | Medium |
| 5 | Query Processing | 6 files | 2 | Low |
| 6 | Content Generation | 4 files | 1 | Low |

---

## Import Trace Commands

Before deleting any file, run:

```bash
# Find all imports of a file
grep -rn "from utils.unified_search_engine_updated" .
grep -rn "import unified_search_engine_updated" .

# Find all usages in tabs/
grep -rn "unified_search_engine_updated" tabs/

# Find all usages in app/
grep -rn "unified_search_engine_updated" app/
```

---

## Final Target Structure

```
utils/
├── __init__.py
├── adapters/                    # 12 files (keep all)
├── security/                    # 4 files (keep all)
├── monitoring/                  # 5 files (keep all)
├── ml_models/                   # 5 files (keep all)
├── ml_training/                 # 3 files (keep all)
├── backup/                      # 3 files (keep for reference)
│
├── # Core Infrastructure (15 files)
├── weaviate_manager.py
├── multi_vector_storage_manager.py
├── multi_vector_storage_interface.py
├── llm_config.py
├── index_manager.py
├── embedding_generator.py
├── notification_manager.py
├── user_feedback_system.py
├── query_cache.py
├── unified_vector_store.py
├── vector_db_provider.py
├── response_writer.py
├── text_cleaning.py
├── ingestion_queue.py
├── ingestion_validator.py
│
├── # Enterprise (10 files)
├── enterprise_*.py
│
├── # Consolidated (10 files)
├── unified_search_engine.py
├── multi_source_search.py
├── simple_search.py
├── document_processor.py
├── image_processor.py
├── chunking_strategy.py
├── chunking_config.py
├── query_processor.py
├── query_result_formatter.py
├── content_generator.py
│
└── # Total: ~60 files
```

---

**Document Version:** 1.0  
**Last Updated:** May 15, 2026
