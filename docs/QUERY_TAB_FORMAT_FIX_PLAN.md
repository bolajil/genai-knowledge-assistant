# Query Tab Format Fix Plan

## Problem Analysis

Your output shows:
```
Executive Summary: regular/special Board meeting.. Notwithstanding subsection 1, above, during the Development Period, a Board

Detailed Answer: Declarations, these Bylaws, and the rules and regulations of the

Key Points: The name of the Association 1s Pecan Ridge Community Association, Inc. Principal Office
```

### Root Causes Identified:

1. **LLM Response Failing** - The enhanced_llm_integration is likely timing out or failing
2. **Fallback Processing Issues** - The fallback creates incomplete sentences
3. **Over-Aggressive Sanitization** - `_sanitize_ai_markdown()` removes too much content
4. **Poor Sentence Extraction** - Simple `.split('.')` doesn't handle complex legal text
5. **Low Relevance Scores** (63%, 6%, 1.9%) - Wrong content being retrieved

## Proposed Fixes

### Fix 1: Improve LLM Prompt (CRITICAL)
**File**: `utils/enhanced_llm_integration.py`
**Issue**: Prompt is too long (900+ lines), causing timeouts
**Solution**: Simplify prompt, increase max_tokens to 1200, add timeout handling

### Fix 2: Better Fallback Processing
**File**: `utils/enhanced_llm_integration.py` - `_fallback_processing()`
**Issue**: Uses simple sentence splitting that breaks mid-sentence
**Solution**: Use QueryResultFormatter.extract_complete_sentences()

### Fix 3: Fix Sanitization Function
**File**: `tabs/query_assistant.py` - `_sanitize_ai_markdown()`
**Issue**: Removes valid content, too aggressive filtering
**Solution**: Only remove obvious noise (TOC, dotted leaders), keep substantive content

### Fix 4: Improve Query Expansion
**File**: `tabs/query_assistant.py` - `_expand_query_variations()`
**Issue**: Not finding relevant content for "board responsibilities"
**Solution**: Add better synonyms and semantic variations

### Fix 5: Better Result Normalization
**File**: `tabs/query_assistant.py` - `_normalize_content_from_result()`
**Issue**: Not extracting page numbers and sections properly
**Solution**: Improve metadata extraction from results

## Implementation Priority

### P0 (Critical - Do Now):
1. ✅ Fix fallback processing to use QueryResultFormatter
2. ✅ Reduce LLM prompt length and increase max_tokens
3. ✅ Fix _sanitize_ai_markdown to be less aggressive

### P1 (High - Next):
4. Improve query expansion for better retrieval
5. Add better error handling and logging
6. Implement result quality validation

### P2 (Medium - Later):
7. Add caching for LLM responses
8. Implement retry logic with exponential backoff
9. Add user feedback collection

## Expected Outcome

### Before (Current):
```
Executive Summary
regular/special Board meeting.. Notwithstanding subsection 1, above

Key Points
The name of the Association 1s Pecan Ridge Community Association, Inc.
```

### After (Fixed):
```
### Executive Summary
The Board of Directors is responsible for managing all affairs of the Association, including conducting regular and special meetings, maintaining records, and ensuring compliance with governing documents.

### Detailed Answer
According to the Bylaws (Page 15, Section 6): The Board of Directors has comprehensive authority to manage the Association's affairs. This includes the power to adopt rules and regulations, approve budgets, and make decisions between member meetings.

The Board must hold regular meetings as specified in the Bylaws, with proper notice to members. Special meetings may be called by the President or a majority of directors.

### Key Points
1. **The Board manages all Association affairs and has authority to adopt rules, approve budgets, and make binding decisions.** _(Source: Bylaws, Page 15, Section: Powers of the Board)_

2. **Regular Board meetings must be held with proper notice to members, and special meetings can be called by the President or majority of directors.** _(Source: Bylaws, Page 16, Section: Meetings)_

3. **The Board is responsible for maintaining accurate records, financial statements, and ensuring compliance with all governing documents.** _(Source: Bylaws, Page 24, Section: Books and Records)_

### Sources
**1. Bylaws** (Page 15)
- 📑 Section: Powers of the Board | 🟢 High Relevance: 87.3%
- **Excerpt**: The Board of Directors is responsible for the affairs of the Association and has comprehensive powers for administration...
```

## Testing Plan

1. **Clear Cache**: Run `python clear_query_cache.py`
2. **Restart App**: `streamlit run genai_dashboard_modular.py`
3. **Test Query**: "What are the responsibilities of Board Members?"
4. **Verify Output**: Check for complete sentences, proper formatting, actual page numbers

## Files to Modify

1. `utils/enhanced_llm_integration.py` - Fix LLM prompt and fallback
2. `tabs/query_assistant.py` - Fix sanitization and normalization
3. `utils/query_result_formatter.py` - Already good, just needs to be used
4. `utils/text_cleaning.py` - May need tweaks for legal text

## Success Criteria

✅ Complete sentences (no "...")
✅ Actual page numbers (not "N/A")
✅ Section information displayed
✅ Professional formatting
✅ High relevance scores (>75%)
✅ No truncated text
✅ Clean, readable output

---

**Status**: Ready to implement
**Priority**: P0 - Critical
**Estimated Time**: 30-45 minutes
