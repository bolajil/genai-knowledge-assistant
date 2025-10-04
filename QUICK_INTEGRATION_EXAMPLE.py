"""
Quick Integration Example for VaultMind Tabs
Copy these snippets into your actual tabs
"""

# ============================================
# EXAMPLE 1: Query Assistant Tab Integration
# ============================================
# Add to tabs/query_assistant.py or tabs/query_assistant_enhanced.py

def enhanced_query_with_intent(query: str, index_name: str):
    """Enhanced query handler with intent classification"""
    import streamlit as st
    from utils.ml_models.query_intent_classifier import get_query_intent_classifier
    from utils.query_helpers import query_index
    
    try:
        # Classify intent
        classifier = get_query_intent_classifier()
        intent_result = classifier.classify_intent(query)
        
        # Show intent to user
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"🎯 **Query Intent**: {intent_result['intent'].title()}")
        with col2:
            st.metric("Confidence", f"{intent_result['confidence']:.0%}")
        
        # Get strategy
        strategy = classifier.get_retrieval_strategy(intent_result['intent'])
        
        # Show strategy
        with st.expander("📊 Retrieval Strategy"):
            st.json(strategy)
        
        # Search with strategy
        results = query_index(
            query=query,
            index_name=index_name,
            top_k=strategy['top_k']
        )
        
        # Format response based on intent
        if intent_result['intent'] == 'factual':
            st.success("**Quick Answer** (Factual Query)")
            # Show concise answer
        elif intent_result['intent'] == 'analytical':
            st.info("**Detailed Analysis** (Analytical Query)")
            # Show detailed reasoning
        elif intent_result['intent'] == 'procedural':
            st.warning("**Step-by-Step Guide** (Procedural Query)")
            # Show steps
        
        return results
        
    except Exception as e:
        st.warning(f"Intent classification unavailable: {e}")
        # Fallback to regular search
        return query_index(query=query, index_name=index_name, top_k=5)


# ============================================
# EXAMPLE 2: Document Ingestion Tab Integration
# ============================================
# Add to tabs/multi_vector_document_ingestion.py

def process_uploaded_file_with_ml(uploaded_file, content: str):
    """Process uploaded file with ML classification and quality checking"""
    import streamlit as st
    from utils.ml_models.document_classifier import get_document_classifier
    from utils.ml_models.data_quality_checker import get_data_quality_checker
    from utils.embedding_generator import generate_embeddings
    
    st.subheader("🤖 AI Analysis")
    
    # Document Classification
    try:
        classifier = get_document_classifier()
        classification = classifier.classify_document(content)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Category", classification['category'].title())
        with col2:
            st.metric("Confidence", f"{classification['confidence']:.0%}")
        with col3:
            keywords = classification['metadata'].get('keywords', [])
            st.metric("Keywords Found", len(keywords))
        
        if keywords:
            st.info(f"🏷️ **Keywords**: {', '.join(keywords[:5])}")
        
    except Exception as e:
        st.warning(f"Classification unavailable: {e}")
        classification = {'category': 'general', 'confidence': 0.0}
    
    # Quality Checking
    try:
        checker = get_data_quality_checker()
        embedding = generate_embeddings([content])[0]
        quality = checker.check_quality(embedding)
        
        # Quality indicator
        if quality['quality_level'] == 'excellent':
            st.success(f"✅ **Quality**: {quality['quality_level'].title()} ({quality['quality_score']:.0%})")
        elif quality['quality_level'] == 'good':
            st.info(f"✓ **Quality**: {quality['quality_level'].title()} ({quality['quality_score']:.0%})")
        elif quality['is_anomaly']:
            st.error(f"⚠️ **Quality Issue**: Anomaly detected!")
            st.warning("This document may be corrupted or very different from your corpus.")
        else:
            st.warning(f"⚠️ **Quality**: {quality['quality_level'].title()} ({quality['quality_score']:.0%})")
        
    except Exception as e:
        st.warning(f"Quality check unavailable: {e}")
        quality = {'quality_score': 1.0, 'is_anomaly': False}
    
    # Recommendation
    if quality['is_anomaly']:
        st.error("❌ **Recommendation**: Reject this document (anomaly detected)")
        return None
    elif quality['quality_score'] < 0.3:
        st.error("❌ **Recommendation**: Reject this document (very low quality)")
        return None
    elif quality['quality_score'] < 0.5:
        st.warning("⚠️ **Recommendation**: Review manually before ingesting")
    else:
        st.success("✅ **Recommendation**: Safe to ingest")
    
    # Return enhanced metadata
    return {
        'filename': uploaded_file.name,
        'category': classification['category'],
        'classification_confidence': classification['confidence'],
        'keywords': classification['metadata'].get('keywords', []),
        'quality_score': quality['quality_score'],
        'quality_level': quality['quality_level'],
        'auto_classified': True,
        'quality_checked': True
    }


# ============================================
# EXAMPLE 3: Streamlit UI Component
# ============================================
# Reusable component for any tab

def show_ml_analysis_panel(query: str = None, content: str = None):
    """Show ML analysis panel in any tab"""
    import streamlit as st
    
    with st.expander("🤖 AI Analysis", expanded=False):
        if query:
            # Query Intent Analysis
            try:
                from utils.ml_models.query_intent_classifier import get_query_intent_classifier
                classifier = get_query_intent_classifier()
                result = classifier.classify_intent(query)
                
                st.write("**Query Intent Analysis**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Intent", result['intent'].title())
                with col2:
                    st.metric("Confidence", f"{result['confidence']:.0%}")
                
                # Show all intents
                st.write("**All Intent Probabilities**")
                for intent, prob in result['all_intents'].items():
                    st.progress(prob, text=f"{intent.title()}: {prob:.0%}")
                    
            except Exception as e:
                st.info(f"Intent analysis unavailable: {e}")
        
        if content:
            # Document Classification
            try:
                from utils.ml_models.document_classifier import get_document_classifier
                classifier = get_document_classifier()
                result = classifier.classify_document(content, return_all_scores=True)
                
                st.write("**Document Classification**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Category", result['category'].title())
                with col2:
                    st.metric("Confidence", f"{result['confidence']:.0%}")
                
                # Show all categories
                if 'all_categories' in result:
                    st.write("**All Category Probabilities**")
                    for category, prob in sorted(result['all_categories'].items(), key=lambda x: x[1], reverse=True)[:5]:
                        st.progress(prob, text=f"{category.title()}: {prob:.0%}")
                        
            except Exception as e:
                st.info(f"Classification unavailable: {e}")


# ============================================
# EXAMPLE 4: Batch Processing
# ============================================
# For processing multiple documents efficiently

def batch_process_documents(documents: list):
    """Process multiple documents efficiently"""
    from utils.ml_models.document_classifier import get_document_classifier
    from utils.ml_models.data_quality_checker import get_data_quality_checker
    from utils.embedding_generator import generate_embeddings
    import streamlit as st
    
    st.write(f"Processing {len(documents)} documents...")
    
    # Batch classification
    classifier = get_document_classifier()
    classifications = classifier.classify_batch([doc['content'] for doc in documents])
    
    # Batch quality checking
    checker = get_data_quality_checker()
    embeddings = generate_embeddings([doc['content'] for doc in documents])
    quality_results = checker.check_batch(embeddings)
    
    # Combine results
    results = []
    for i, doc in enumerate(documents):
        results.append({
            'filename': doc['filename'],
            'category': classifications[i]['category'],
            'confidence': classifications[i]['confidence'],
            'quality_score': quality_results[i]['quality_score'],
            'quality_level': quality_results[i]['quality_level'],
            'is_anomaly': quality_results[i]['is_anomaly']
        })
    
    # Show summary
    st.write("**Processing Summary**")
    
    # Category distribution
    categories = {}
    for r in results:
        categories[r['category']] = categories.get(r['category'], 0) + 1
    
    st.bar_chart(categories)
    
    # Quality distribution
    quality_levels = {}
    for r in results:
        quality_levels[r['quality_level']] = quality_levels.get(r['quality_level'], 0) + 1
    
    st.write("**Quality Distribution**")
    st.json(quality_levels)
    
    return results


if __name__ == "__main__":
    print("This file contains integration examples.")
    print("Copy the functions into your actual tab files.")
    print("See ML_MODELS_INTEGRATION_GUIDE.md for detailed instructions.")
