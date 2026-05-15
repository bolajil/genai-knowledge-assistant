# Pinecone as Primary RAG Store
## Appendix A — Implementation Strategy

---

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| Pinecone in config | ✅ Set as primary | `config/multi_vector_config.yml` |
| PineconeAdapter | ✅ Exists | `utils/adapters/pinecone_adapter.py` |
| Weaviate fallback | ✅ Configured | fallback_stores in config |
| FAISS fallback | ✅ Configured | Local development only |

---

## Three Gaps to Close

### Gap 1: Namespace Isolation (Missing)

**Current:** No tenant/department isolation in Pinecone indexes

**Required:** Index naming pattern: `vaultmind-{tenant}-{dept}-{doctype}`

**Example indexes:**
```
vaultmind-huron-clinical-policies
vaultmind-huron-finance-contracts
vaultmind-huron-hr-procedures
```

**Code change needed in `pinecone_adapter.py`:**
```python
def get_namespace(self, tenant_id: str, dept_id: str, doc_type: str = "general") -> str:
    """Build Pinecone index name from tenant, department, doc type."""
    name = f"vaultmind-{tenant_id}-{dept_id}-{doc_type}"
    name = re.sub(r"[^a-z0-9-]", "-", name.lower())[:45]
    return name
```

---

### Gap 2: Incomplete Metadata on Upsert

**Current metadata:**
- `content`
- `source`
- `source_type`
- `created_at`

**Required additional fields:**
- `department_id` — For filtering
- `tenant_id` — For multi-tenant
- `uploaded_by` — Audit trail
- `sensitivity_level` — Access control (public/internal/confidential/restricted)

**Code change needed:**
```python
metadata = {
    "content":          doc.get("content", "")[:40000],
    "source":           doc.get("source", ""),
    "source_type":      doc.get("source_type", "unknown"),
    "created_at":       doc.get("created_at", datetime.now().isoformat()),
    "department_id":    doc.get("department_id", ""),      # NEW
    "tenant_id":        doc.get("tenant_id", ""),          # NEW
    "uploaded_by":      doc.get("uploaded_by", ""),        # NEW
    "sensitivity_level": doc.get("sensitivity_level", "internal"),  # NEW
}
```

---

### Gap 3: Department Filter Not Enforced on Search

**Current:** Filter parameter passes through but not built from JWT context

**Required:** Auto-inject department filter on every search

**Code change needed:**
```python
# In search(), build dept filter from context
allowed_dept_ids = filters.get("allowed_department_ids", []) if filters else []
pinecone_filter = None
if allowed_dept_ids:
    pinecone_filter = {"department_id": {"$in": allowed_dept_ids}}

search_response = index.query(
    vector=query_embedding,
    top_k=limit,
    include_metadata=True,
    include_values=False,
    filter=pinecone_filter,  # Department scope enforced
)
```

---

## Embedding Model Decision

**⚠️ CRITICAL:** This decision must be made BEFORE first production ingestion. Pinecone indexes are created with fixed vector dimensions.

| Model | Dimensions | Cost | Recommended For |
|-------|------------|------|-----------------|
| `all-MiniLM-L6-v2` | 384 | Free (local) | Development/pilot |
| `text-embedding-3-small` | 1536 | $0.02/1M tokens | **Huron production** ✅ |
| `text-embedding-3-large` | 3072 | $0.13/1M tokens | High-accuracy use cases |

**Recommendation:** Use `text-embedding-3-small` for Huron production
- Strong performance on clinical/legal text
- Reasonable cost for enterprise scale
- Good balance of quality and storage costs

---

## Fallback Chain

```
Primary: Pinecone (semantic search)
    ↓ (if unavailable)
Fallback 1: Weaviate (hybrid search - BM25 + dense)
    ↓ (if unavailable)  
Fallback 2: FAISS (local development only)
```

**Why keep Weaviate as fallback?**
- BM25 hybrid search for drug names, ICD codes, procedure codes
- Dense vector search alone can miss exact term matches
- Pinecone Serverless is pure ANN — no keyword matching

---

## Pinecone Index Naming Rules

- Pattern: `[a-z0-9-]+`
- Max length: 45 characters
- No underscores, spaces, or special characters
- All lowercase

**Valid:** `vaultmind-huron-clinical-policies`  
**Invalid:** `VaultMind_Huron_Clinical` ❌

---

## Implementation Checklist

- [ ] Add `get_namespace()` helper to `pinecone_adapter.py`
- [ ] Extend metadata in `upsert_documents()` method
- [ ] Add department filter injection in `search()` method
- [ ] Choose embedding model (recommendation: `text-embedding-3-small`)
- [ ] Update config with embedding dimension
- [ ] Test tenant isolation with two departments
- [ ] Verify metadata fields visible in Pinecone console

---

## Exit Criteria

- [ ] All three code changes merged
- [ ] Embedding model decision documented
- [ ] Tenant isolation test passes
- [ ] Pinecone console shows separate indexes per department
- [ ] Each vector has all 8 metadata fields

---

**Document Version:** 1.0  
**Last Updated:** May 15, 2026
