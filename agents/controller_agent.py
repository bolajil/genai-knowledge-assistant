# controller_agent.py
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Initialize embeddings - keep this consistent with your indexing
EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vector_store(index_name):
    """Get vector store for the specified index"""
    persist_dir = f"vectors/{index_name}"
    return Chroma(persist_directory=persist_dir, embedding_function=EMBEDDINGS)

def retrieve_documents(prompt: str, index_name: str, k=5) -> list:
    """Retrieve relevant documents with source metadata"""
    vector_store = get_vector_store(index_name)
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.5}
    )
    return retriever.get_relevant_documents(prompt)

def format_context_with_sources(docs) -> str:
    """Format documents with source citations"""
    context = ""
    for i, doc in enumerate(docs):
        source = doc.metadata.get('source', 'Unknown Document')
        page = doc.metadata.get('page', 'N/A')
        context += f"[[Source {i+1}]] {source} (Page {page}):\n{doc.page_content}\n\n"
    return context

def score_claude(prompt: str) -> float:
    score = 0.5
    if "summarize" in prompt.lower(): score += 0.4
    if "summarize" in prompt.lower(): score += 0.2
    return score

def score_gpt(prompt: str) -> float:
    score = 0.5
    if "summarize" in prompt.lower(): score += 0.4
    if "summarize" in prompt.lower(): score += 0.2
    return score

def score_deepseek(prompt: str) -> float:
    return 0.75 if "math" in prompt.lower() or "calculate" in prompt.lower() else 0.4

def score_anthropic(prompt: str) -> float:
    return 0.8 if "ethics" in prompt.lower() or "safe" in prompt.lower() else 0.45

def choose_provider(prompt: str, index_name: str, override: str = None) -> str:
    scores = {
        "claude": score_claude(prompt),
        "gpt": score_gpt(prompt),
        "deepseek": score_deepseek(prompt),
        "anthropic": score_anthropic(prompt)
    }

    print("🔍 Provider Scores:", scores)
    return max(scores, key=scores.get)

def generate_prompt(prompt: str, index_name: str) -> tuple:
    """Generate enhanced prompt with context and source citations"""
    # Retrieve relevant documents
    docs = retrieve_documents(prompt, index_name)
    
    # Format context with source markers
    context = format_context_with_sources(docs)
    
    # Extract source metadata for UI display
    sources = []
    for doc in docs:
        source = doc.metadata.get('source', '')
        if source and source not in sources:
            # Get just the filename
            sources.append(os.path.basename(source))
    
    # Create the enhanced prompt
    enhanced_prompt = f"""
    You are an expert analyst for HOA documents. Answer the question based ONLY on the following context.
    Cite sources using [[Source #]] notation after relevant statements.
    If context is insufficient, say "I couldn't find definitive information".
    
    Context:
    {context}
    
    Question: {prompt}
    
    Response Guidelines:
    1. Answer in markdown format with clear sections
    2. Always cite sources after key statements
    3. Never speculate or invent information
    4. Highlight key terms in bold
    5. Include a "Sources" section at the end listing all references
    """
    
    return enhanced_prompt, sources
