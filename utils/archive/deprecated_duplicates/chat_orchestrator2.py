# utils/chat_orchestrator.py

def build_prompt(query: str, chunks: list[str], provider: str) -> str:
    context = "\n\n".join(chunks[:5]) if chunks else ""
    
    if provider in ["openai", "claude", "deepseek"]:
        return f"""You are a helpful AI assistant. Use the following context to answer the user's question.

Context:
{context}

Question: {query}
Answer:"""

    elif provider == "ollama":
        return f"[INST] Use the context below to answer:\n\n{context}\n\n[QUERY] {query}"

    return f"Context:\n{context}\n\nQuestion:\n{query}"



def call_llm(prompt: str, provider: str) -> str:
    # Placeholder for LLM provider integration
    # We'll scaffold this next
    return f"🤖 [Simulated response from {provider}]\n\n{prompt[:500]}..."
