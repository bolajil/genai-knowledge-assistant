# Critical Issues — Immediate Attention Required

## 🔴 Issue #1: Merge Conflict in `.env.example`

**Status:** BLOCKING  
**File:** `@.env.example:75-84`

```
<<<<<<< HEAD

# --- Web Search Configuration ---
# Bing Web Search API (Recommended for production)
BING_SEARCH_API_KEY=your_bing_search_api_key_here

# Note: DuckDuckGo search works automatically...
=======
>>>>>>> clean-master
```

**Impact:** 
- Any new developer cloning the repo sees unprofessional conflict markers
- Blocks clean configuration setup

**Fix:** Remove markers, keep the web search configuration section

---

## 🔴 Issue #2: Personal Data in Git History

**Status:** BLOCKING for Huron demo  
**Folders:**
- `archive_cleanup_2024/`
- `archive_cleanup_20250919_082734/`
- `archive_conflict_backups/`

**Impact:**
- Personal document chunks visible in git history
- Professional review concern
- Potential data exposure

**Fix:** 
```bash
git filter-repo --path archive_cleanup_20250919_082734 --invert-paths
git filter-repo --path archive_cleanup_2024 --invert-paths
# Force push after backup
```

---

## 🔴 Issue #3: JWT Secret Fallback

**Status:** SECURITY RISK  
**Location:** `app/auth/authentication.py`

**Current behavior:** Falls back to hardcoded string if `JWT_SECRET_KEY` env var is not set

**Impact:**
- Security vulnerability in production
- HIPAA compliance concern

**Fix:** Remove fallback, raise `ValueError` at startup if env var missing

---

## 🟠 Issue #4: No Tenant Isolation

**Status:** DEMO BLOCKER for Huron  
**Impact:**
- Cannot demonstrate "HR can't see Finance documents"
- No department scoping on documents
- No multi-tenant architecture

**Fix:** Phase 2 implementation (PostgreSQL + Weaviate namespace isolation)

---

## 🟠 Issue #5: No Audit Logging

**Status:** HIPAA COMPLIANCE GAP  
**Impact:**
- Cannot demonstrate audit trail
- HIPAA §164.312(b) requires audit controls

**Fix:** Phase 4 implementation (AuditService + audit_events table)

---

## 🟡 Issue #6: Streamlit as Primary Interface

**Status:** ARCHITECTURE CONCERN  
**Impact:**
- Cannot scale independently
- Cannot add API gateway/WAF
- Cannot generate SDK
- Other frontends cannot consume

**Fix:** Phase 3 implementation (FastAPI as primary, Streamlit as debug tool)

---

## Summary: Critical Path

```
[MUST FIX BEFORE DEMO]
   ↓
1. .env.example conflict ──────────► 5 minutes
   ↓
2. Purge archive folders ──────────► 30 minutes (with backup)
   ↓
3. Repo cleanup (root .md files) ──► 1 day
   ↓
4. PostgreSQL + tenant schema ─────► 3 days
   ↓
5. Tenant isolation tests ─────────► 1 day
   ↓
[READY FOR HURON DEMO]
```

---

**Document Version:** 1.0  
**Last Updated:** May 15, 2026
