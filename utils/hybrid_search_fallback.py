from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def hybrid_search_fallback(query, pages, top_k=3):
    """
    TF-IDF hybrid search fallback for immediate improvement over keyword matching.
    """
    query_lower = query.lower()
    
    # Create a list of page texts
    page_texts = [page.strip() for page in pages if page.strip()]

    if query_lower and page_texts:
        # Calculate TF-IDF vectors
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(page_texts)
        
        # Transform query into TF-IDF vector
        query_vec = vectorizer.transform([query_lower])
        
        # Calculate cosine similarity between query and each page
        cos_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        
        # Get top-k page indices
        top_page_indices = cos_similarities.argsort()[-top_k:][::-1]
        
        # Build results from top pages
        results = []
        for idx in top_page_indices:
            if cos_similarities[idx] > 0: # Only include if somewhat relevant
                content = page_texts[idx]
                if len(content) > 1000:
                    content = content[:1000] + "..."
                results.append(f"[Relevance: {cos_similarities[idx]:.3f}] From index:\n\n{content}")
        
        return results
    
    return []
