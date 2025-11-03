"""
Document Quality UI Components
Streamlit UI for checking and cleaning document quality
"""

import streamlit as st
from typing import Tuple, Optional
from utils.document_quality_checker import (
    DocumentQualityChecker,
    DocumentCleaner,
    get_quality_emoji,
    get_quality_label
)


def render_quality_check_ui(text: str, file_name: str = "document") -> Tuple[str, bool]:
    """
    Render quality check UI and return cleaned text if user chooses to clean
    
    Args:
        text: Original text content
        file_name: Name of the file being checked
        
    Returns:
        Tuple of (text_to_use, was_cleaned)
    """
    if not text or len(text.strip()) == 0:
        st.warning("⚠️ Document appears to be empty")
        return text, False
    
    # Initialize checker
    checker = DocumentQualityChecker()
    cleaner = DocumentCleaner()
    
    # Analyze quality
    with st.spinner("🔍 Analyzing document quality..."):
        analysis = checker.analyze_text(text)
    
    quality_score = analysis['quality_score']
    issues = analysis['issues']
    stats = analysis['stats']
    recommendations = analysis['recommendations']
    
    # Display quality score
    st.markdown("### 📊 Document Quality Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        emoji = get_quality_emoji(quality_score)
        label = get_quality_label(quality_score)
        st.metric(
            "Quality Score",
            f"{quality_score:.2f}",
            delta=label,
            delta_color="normal" if quality_score >= 0.5 else "inverse"
        )
    
    with col2:
        st.metric("Total Words", f"{stats['total_words']:,}")
    
    with col3:
        st.metric("Issues Found", len(issues))
    
    # Show issues if any
    if issues:
        st.markdown("#### 🔍 Issues Detected")
        for issue in issues:
            severity_emoji = "🔴" if issue.severity == "high" else "🟡" if issue.severity == "medium" else "🟢"
            with st.expander(f"{severity_emoji} {issue.description} ({issue.count} occurrences)"):
                st.write(f"**Severity:** {issue.severity.title()}")
                if issue.examples:
                    st.write("**Examples:**")
                    for example in issue.examples[:5]:
                        st.code(example, language=None)
    
    # Show recommendations
    if recommendations:
        st.markdown("#### 💡 Recommendations")
        for rec in recommendations:
            st.write(rec)
    
    # Cleaning options
    if quality_score < 0.8:
        st.markdown("---")
        st.markdown("### 🧹 Document Cleaning")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("Would you like to automatically clean this document?")
            st.info("💡 Cleaning will fix missing spaces, remove repeated characters, and improve text quality.")
        
        with col2:
            aggressive_mode = st.checkbox(
                "Aggressive Mode",
                value=False,
                help="Apply more aggressive cleaning (may alter more text)"
            )
        
        # Preview cleaning
        if st.button("👁️ Preview Cleaning", key=f"preview_{file_name}"):
            with st.spinner("Generating preview..."):
                preview = cleaner.preview_cleaning(text, max_length=1000)
            
            st.markdown("#### Before vs After")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Before:**")
                st.text_area(
                    "Original",
                    preview['before_sample'],
                    height=200,
                    key=f"before_{file_name}",
                    label_visibility="collapsed"
                )
            
            with col2:
                st.markdown("**After:**")
                st.text_area(
                    "Cleaned",
                    preview['after_sample'],
                    height=200,
                    key=f"after_{file_name}",
                    label_visibility="collapsed"
                )
            
            st.markdown("**Changes:**")
            changes_col1, changes_col2, changes_col3 = st.columns(3)
            with changes_col1:
                st.metric("Spaces Added", preview['changes']['spaces_added'])
            with changes_col2:
                st.metric("Repeated Chars Removed", preview['changes']['repeated_chars_removed'])
            with changes_col3:
                st.metric("Special Chars Removed", preview['changes']['special_chars_removed'])
        
        # Clean button
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✨ Clean Document", type="primary", key=f"clean_{file_name}"):
                with st.spinner("🧹 Cleaning document..."):
                    cleaned_text, changes = cleaner.clean_text(text, aggressive=aggressive_mode)
                
                # Show what changed
                st.success("✅ Document cleaned successfully!")
                
                change_col1, change_col2, change_col3, change_col4 = st.columns(4)
                with change_col1:
                    st.metric("Spaces Added", changes['spaces_added'])
                with change_col2:
                    st.metric("Repeated Removed", changes['repeated_chars_removed'])
                with change_col3:
                    st.metric("Special Removed", changes['special_chars_removed'])
                with change_col4:
                    st.metric("Words Split", changes['words_split'])
                
                # Re-analyze cleaned text
                new_analysis = checker.analyze_text(cleaned_text)
                new_score = new_analysis['quality_score']
                
                improvement = new_score - quality_score
                st.metric(
                    "New Quality Score",
                    f"{new_score:.2f}",
                    delta=f"+{improvement:.2f}" if improvement > 0 else f"{improvement:.2f}"
                )
                
                return cleaned_text, True
        
        with col2:
            if st.button("➡️ Use Original", key=f"original_{file_name}"):
                st.info("Using original document without cleaning")
                return text, False
    
    else:
        st.success("✅ Document quality is good - no cleaning needed!")
    
    return text, False


def render_quick_quality_badge(text: str) -> None:
    """
    Render a quick quality badge (for use in lists/previews)
    
    Args:
        text: Text to analyze
    """
    if not text:
        return
    
    checker = DocumentQualityChecker()
    analysis = checker.analyze_text(text)
    quality_score = analysis['quality_score']
    
    emoji = get_quality_emoji(quality_score)
    label = get_quality_label(quality_score)
    
    if quality_score >= 0.8:
        st.success(f"{emoji} Quality: {label} ({quality_score:.2f})")
    elif quality_score >= 0.5:
        st.warning(f"{emoji} Quality: {label} ({quality_score:.2f})")
    else:
        st.error(f"{emoji} Quality: {label} ({quality_score:.2f})")


def render_batch_quality_check(texts: dict) -> dict:
    """
    Check quality of multiple documents
    
    Args:
        texts: Dict of {name: text_content}
        
    Returns:
        Dict of {name: analysis_result}
    """
    checker = DocumentQualityChecker()
    
    st.markdown("### 📊 Batch Quality Analysis")
    
    results = {}
    progress_bar = st.progress(0)
    
    for i, (name, text) in enumerate(texts.items()):
        analysis = checker.analyze_text(text)
        results[name] = analysis
        progress_bar.progress((i + 1) / len(texts))
    
    progress_bar.empty()
    
    # Summary table
    import pandas as pd
    
    summary_data = []
    for name, analysis in results.items():
        summary_data.append({
            'Document': name,
            'Quality': f"{analysis['quality_score']:.2f}",
            'Status': get_quality_label(analysis['quality_score']),
            'Issues': len(analysis['issues']),
            'Words': analysis['stats']['total_words']
        })
    
    df = pd.DataFrame(summary_data)
    st.dataframe(df, use_container_width=True)
    
    # Show which need cleaning
    needs_cleaning = [name for name, analysis in results.items() if analysis['quality_score'] < 0.8]
    
    if needs_cleaning:
        st.warning(f"⚠️ {len(needs_cleaning)} document(s) may benefit from cleaning:")
        for name in needs_cleaning:
            st.write(f"  • {name}")
    else:
        st.success("✅ All documents have good quality!")
    
    return results


# Example usage in ingestion tab
def integrate_with_ingestion():
    """
    Example of how to integrate into document ingestion
    """
    st.markdown("## Example Integration")
    
    # Simulated file upload
    uploaded_file = st.file_uploader("Upload document", type=['txt', 'pdf'])
    
    if uploaded_file:
        # Extract text (simplified)
        text = uploaded_file.getvalue().decode('utf-8')
        
        # Show quality check UI
        cleaned_text, was_cleaned = render_quality_check_ui(text, uploaded_file.name)
        
        # Use cleaned_text for ingestion
        if was_cleaned:
            st.success("✅ Using cleaned version for ingestion")
        else:
            st.info("ℹ️ Using original version for ingestion")
        
        # Continue with normal ingestion...
        if st.button("Continue to Ingestion"):
            st.write(f"Would ingest {len(cleaned_text)} characters...")


if __name__ == "__main__":
    # Demo
    st.set_page_config(page_title="Document Quality Checker", layout="wide")
    
    st.title("📊 Document Quality Checker Demo")
    
    # Sample problematic text
    sample_text = st.text_area(
        "Enter text to analyze:",
        value="""TheQuickBrownFoxJumpsOverTheLazyDog
thisisaverylongwordwithoutanyspaces
Hellooooooo World!!!!
This is normal text with proper spacing.
""",
        height=200
    )
    
    if st.button("Analyze"):
        cleaned, was_cleaned = render_quality_check_ui(sample_text, "sample.txt")
        
        if was_cleaned:
            st.markdown("### Final Cleaned Text")
            st.text_area("Result", cleaned, height=200)
