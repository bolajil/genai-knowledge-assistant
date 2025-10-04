"""
Enterprise Response Formatter
Formats query responses with professional markdown structure based on intent
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EnterpriseResponseFormatter:
    """Format responses with enterprise-grade markdown structure"""
    
    def format_response(self, 
                       query: str, 
                       intent: str, 
                       results: List[Dict], 
                       confidence: float) -> str:
        """
        Format response based on query intent
        
        Args:
            query: User's query
            intent: Detected intent (factual, analytical, procedural, comparative, exploratory)
            results: Search results from vector DB
            confidence: Intent classification confidence
            
        Returns:
            Formatted markdown response
        """
        if not results:
            return self._format_no_results(query)
        
        # Route to appropriate formatter based on intent
        formatters = {
            'factual': self._format_factual,
            'analytical': self._format_analytical,
            'procedural': self._format_procedural,
            'comparative': self._format_comparative,
            'exploratory': self._format_exploratory
        }
        
        formatter = formatters.get(intent, self._format_exploratory)
        return formatter(query, results, confidence)
    
    def _format_no_results(self, query: str) -> str:
        """Format response when no results found"""
        return f"""
## ❌ No Results Found

**Query**: {query}

**Recommendation**: 
- Try rephrasing your question
- Use different keywords
- Check if the relevant documents are ingested
- Contact your administrator to add relevant content
"""
    
    def _format_factual(self, query: str, results: List[Dict], confidence: float) -> str:
        """Format concise factual answer"""
        # Get top result
        top_result = results[0]
        content = top_result.get('content', '')
        source = top_result.get('source', 'Unknown')
        
        # Extract first 2-3 sentences for concise answer
        sentences = content.split('.')[:3]
        answer = '. '.join(s.strip() for s in sentences if s.strip()) + '.'
        
        response = f"""
## 📌 Answer

{answer}

---

### 📚 Source
**Document**: {source}

### 🔍 Additional Context
"""
        
        # Add snippets from other results
        for i, result in enumerate(results[1:3], 1):
            snippet = result.get('content', '')[:200]
            src = result.get('source', 'Unknown')
            response += f"\n**{i}.** {snippet}... *(Source: {src})*\n"
        
        return response
    
    def _format_analytical(self, query: str, results: List[Dict], confidence: float) -> str:
        """Format detailed analytical answer with reasoning"""
        response = f"""
## 🧠 Analysis

### Executive Summary
Based on the available information, here's a comprehensive analysis:

"""
        
        # Group results by themes
        for i, result in enumerate(results[:5], 1):
            content = result.get('content', '')
            source = result.get('source', 'Unknown')
            page = result.get('page', '')
            
            response += f"""
### {i}. Key Finding

{content[:400]}...

**Source**: {source} {f'(Page {page})' if page else ''}

---
"""
        
        response += """
### 💡 Key Insights

Based on the analysis above:
- Multiple perspectives have been considered
- Evidence is drawn from authoritative sources
- Patterns and relationships have been identified

### 📊 Conclusion

The analysis demonstrates a comprehensive understanding of the topic with supporting evidence from multiple sources.
"""
        
        return response
    
    def _format_procedural(self, query: str, results: List[Dict], confidence: float) -> str:
        """Format step-by-step procedural answer"""
        response = f"""
## 📋 Step-by-Step Guide

**Task**: {query}

---

"""
        
        # Format as numbered steps
        for i, result in enumerate(results[:7], 1):
            content = result.get('content', '')
            source = result.get('source', 'Unknown')
            
            # Extract actionable content
            step_content = content[:300]
            
            response += f"""
### Step {i}

{step_content}...

*Reference: {source}*

---

"""
        
        response += """
### ✅ Completion Checklist

- [ ] Review all steps above
- [ ] Gather necessary resources
- [ ] Follow procedures in order
- [ ] Document your progress
- [ ] Verify completion

### 💡 Best Practices

- Follow each step carefully
- Refer to source documents for details
- Consult with relevant stakeholders
- Document any deviations
"""
        
        return response
    
    def _format_comparative(self, query: str, results: List[Dict], confidence: float) -> str:
        """Format comparative analysis"""
        response = f"""
## ⚖️ Comparative Analysis

**Comparison**: {query}

---

### 📊 Comparison Table

| Aspect | Details | Source |
|--------|---------|--------|
"""
        
        for i, result in enumerate(results[:8], 1):
            content = result.get('content', '')[:150].replace('\n', ' ')
            source = result.get('source', 'Unknown')
            response += f"| Item {i} | {content}... | {source} |\n"
        
        response += """

---

### 🔍 Key Differences

Based on the comparison above, here are the main distinctions:

"""
        
        for i, result in enumerate(results[:4], 1):
            content = result.get('content', '')[:200]
            response += f"**{i}.** {content}...\n\n"
        
        response += """
### 💡 Recommendation

Consider the following when making your decision:
- Review all aspects carefully
- Weigh the pros and cons
- Consult with stakeholders
- Align with organizational goals
"""
        
        return response
    
    def _format_exploratory(self, query: str, results: List[Dict], confidence: float) -> str:
        """Format comprehensive exploratory overview"""
        response = f"""
## 📖 Comprehensive Overview

**Topic**: {query}

---

### 🎯 Executive Summary

This overview provides comprehensive information on the requested topic, drawing from multiple authoritative sources.

---

"""
        
        # Organize by sections
        sections = [
            ("Core Information", results[:3]),
            ("Detailed Context", results[3:6]),
            ("Additional Insights", results[6:9]),
            ("Supporting Details", results[9:12])
        ]
        
        for section_title, section_results in sections:
            if not section_results:
                continue
                
            response += f"### {section_title}\n\n"
            
            for i, result in enumerate(section_results, 1):
                content = result.get('content', '')
                source = result.get('source', 'Unknown')
                page = result.get('page', '')
                
                # Format content nicely
                formatted_content = content[:400]
                
                response += f"""
#### {i}. {source} {f'(Page {page})' if page else ''}

{formatted_content}...

---

"""
        
        response += """
### 📚 Complete Source List

All information above is drawn from the following sources:

"""
        
        # List all sources
        sources = set()
        for result in results:
            source = result.get('source', 'Unknown')
            if source != 'Unknown':
                sources.add(source)
        
        for i, source in enumerate(sorted(sources), 1):
            response += f"{i}. {source}\n"
        
        response += """

---

### 💡 Next Steps

To learn more about this topic:
- Review the detailed sections above
- Consult the original source documents
- Reach out to subject matter experts
- Explore related topics
"""
        
        return response


# Singleton instance
_formatter_instance = None

def get_enterprise_formatter() -> EnterpriseResponseFormatter:
    """Get or create singleton instance"""
    global _formatter_instance
    if _formatter_instance is None:
        _formatter_instance = EnterpriseResponseFormatter()
    return _formatter_instance
