# controller_agent.py - CLEAN VERSION
import os
import json
from pathlib import Path
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS, Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.utils.embeddings import get_embeddings
from utils.simple_vector_manager import get_simple_index_path  # Import the simple path finder

# MCP imports with fallback
try:
    from app.mcp.protocol import ModelContext
    from app.mcp.function_calling import FunctionHandler
except ImportError:
    # Create dummy classes if MCP not yet implemented
    print("⚠️ MCP modules not found, using fallback classes")
    
    class ModelContext:
        def __init__(self):
            self.model_name = "gpt-3.5-turbo"
            self.parameters = {}
        
        def get_from_memory(self, key):
            return None
        
        def save_to_memory(self, key, value):
            pass
        
        def add_to_memory(self, key, value):
            pass
    
    class FunctionHandler:
        @staticmethod
        def get_definitions():
            return []
        
        @staticmethod
        def execute(name, args):
            return {}


def get_valid_retriever(index_name: str):
    """Load a retriever for the specified index, handling different index types."""
    if not index_name or index_name == "General Knowledge":
        return None

    try:
        print(f"Loading index: {index_name}")
        
        # Use the simple vector manager to find the correct path
        index_path = get_simple_index_path(index_name)

        if not index_path:
            print(f"Index '{index_name}' not found in any known location.")
            return None

        # Check if this is a text-based index (like ByLaw)
        from pathlib import Path
        if (Path(index_path) / "extracted_text.txt").exists():
            print(f"Using enhanced text retrieval for {index_name}")
            # Create a custom retriever for text-based indexes
            return TextBasedRetriever(index_path, index_name)
        
        # Try to load as FAISS index
        embedding_model = get_embeddings()
        db = FAISS.load_local(index_path, embedding_model, allow_dangerous_deserialization=True)
        retriever = db.as_retriever(search_kwargs={"k": 4})
        print(f"Successfully loaded FAISS retriever for index: {index_name}")
        return retriever
        
    except Exception as e:
        print(f"Failed to load index '{index_name}': {e}")
        return None

class TextBasedRetriever:
    """Custom retriever for text-based indexes like ByLaw"""
    def __init__(self, index_path: str, index_name: str):
        self.index_path = index_path
        self.index_name = index_name
    
    def get_relevant_documents(self, query: str):
        """Get relevant documents using enhanced text search"""
        try:
            from utils.enhanced_retrieval import search_bylaw_content
            chunks = search_bylaw_content(query, self.index_path, max_results=4)
            return chunks
        except Exception as e:
            print(f"Error in text-based retrieval: {e}")
            return []

def get_chat_chain(context: ModelContext, retriever):
    """Create a chat chain with or without a retriever, including a timeout."""
    # Prevent older OpenAI SDKs from receiving unsupported 'project' kwarg via env
    try:
        os.environ.pop("OPENAI_PROJECT", None)
    except Exception:
        pass

    llm = ChatOpenAI(
        model=context.model_name,
        temperature=context.parameters.get("temperature", 0.7),
        max_tokens=context.parameters.get("max_tokens", 1500),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        request_timeout=60  # Add a 60-second timeout to prevent hanging
    )

    if retriever:
        # Create a RetrievalQA chain for document-based tasks
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
    else:
        # Return the LLM directly for general knowledge tasks
        return llm

def execute_agent(user_prompt: str, context: ModelContext, index_name: str) -> dict:
    """Execute the agent with enterprise-enhanced retrieval and structured output."""
    try:
        if index_name == "General Knowledge":
            # General Knowledge Task
            print("Executing General Knowledge Task")
            llm = get_chat_chain(context, retriever=None)
            response = llm.invoke(user_prompt)
            return {"result": response.content, "source_documents": []}
        else:
            # Enterprise Document-based Task
            print(f"Executing Enterprise Document Task on index: {index_name}")
            
            # Try enterprise integration first
            try:
                from utils.enterprise_integration_layer import enterprise_enhanced_query
                
                # Determine response type based on index
                response_type = "legal" if "bylaw" in index_name.lower() or "legal" in index_name.lower() else "general"
                
                # Use enterprise enhanced query
                enterprise_result = enterprise_enhanced_query(
                    query=user_prompt,
                    index_name=index_name,
                    max_results=5,
                    response_type=response_type,
                    use_cache=False  # Real-time should not cache
                )
                
                if enterprise_result and enterprise_result.get('source_documents'):
                    print(f"Enterprise retrieval successful: {len(enterprise_result['source_documents'])} sources")
                    
                    # Create enhanced prompt with structured context
                    context_text = "\n\n".join([
                        f"Source: {result.get('source', 'Unknown')}\nPage: {result.get('page', 'N/A')}\nContent: {result.get('content', '')}"
                        for result in enterprise_result['source_documents'][:5]
                    ])
                    
                    enhanced_prompt = f"""Based on the following document content, provide a comprehensive answer to the user's question.

User Question: {user_prompt}

Document Content:
{context_text}

Please provide a detailed, accurate response based solely on the document content above. Include specific references to pages and sections where relevant."""
                    
                    # Get LLM response
                    llm = get_chat_chain(context, retriever=None)
                    response = llm.invoke(enhanced_prompt)
                    
                    # Format source documents for compatibility
                    source_docs = []
                    for result in enterprise_result['source_documents']:
                        source_docs.append({
                            'page_content': result.get('content', ''),
                            'metadata': {
                                'source': result.get('source', 'Unknown'),
                                'page': result.get('page', 'N/A'),
                                'section': result.get('section', 'N/A'),
                                'enterprise_scores': result.get('metadata', {})
                            }
                        })
                    
                    # Log feedback data for enterprise retrieval
                    from utils.user_feedback_system import log_query_feedback
                    
                    # Calculate average confidence from enterprise scores
                    avg_confidence = 0.0
                    if source_docs:
                        confidence_scores = []
                        for doc in source_docs:
                            enterprise_scores = doc.get('metadata', {}).get('enterprise_scores', {})
                            if isinstance(enterprise_scores, dict):
                                # Extract confidence from various score types
                                if 'confidence_score' in enterprise_scores:
                                    confidence_scores.append(enterprise_scores['confidence_score'])
                                elif 'similarity_score' in enterprise_scores:
                                    confidence_scores.append(enterprise_scores['similarity_score'])
                                elif 'relevance_score' in enterprise_scores:
                                    confidence_scores.append(enterprise_scores['relevance_score'])
                        
                        if confidence_scores:
                            avg_confidence = sum(confidence_scores) / len(confidence_scores)
                    
                    return {
                        "result": response.content,
                        "source_documents": source_docs,
                        "enterprise_features_used": enterprise_result.get('enterprise_features_used', []),
                        "retrieval_method": "enterprise_hybrid",
                        "confidence_score": avg_confidence,
                        "feedback_ready": True  # Flag to indicate feedback can be collected
                    }
                    
            except Exception as e:
                print(f"Enterprise retrieval failed, falling back to real-time: {e}")
            
            # New: Try standard retriever (FAISS or text) before real-time disk read
            try:
                retriever = get_valid_retriever(index_name)
            except Exception as _rerr:
                retriever = None
            if retriever is not None:
                try:
                    chain = get_chat_chain(context, retriever)
                    qa_out = chain.invoke(user_prompt)
                    # LangChain RetrievalQA returns a dict with 'result' and 'source_documents'
                    if isinstance(qa_out, dict):
                        result_text = qa_out.get("result", "")
                        docs = qa_out.get("source_documents", []) or []
                    else:
                        # Fallback if an unexpected type is returned
                        result_text = str(getattr(qa_out, "content", qa_out))
                        docs = []

                    src_docs = []
                    for d in docs:
                        try:
                            src_docs.append({
                                'page_content': getattr(d, 'page_content', ''),
                                'metadata': getattr(d, 'metadata', {}) or {}
                            })
                        except Exception:
                            pass

                    if result_text:
                        return {
                            "result": result_text,
                            "source_documents": src_docs,
                            "retrieval_method": "faiss_or_text_retriever"
                        }
                except Exception as _qa_err:
                    # If retriever path fails, continue to real-time fallback below
                    pass

            # Fallback to real-time retrieval
            from utils.real_time_retrieval import get_real_time_retriever, verify_fresh_content
            
            # Verify content freshness
            verification = verify_fresh_content(user_prompt, index_name)
            print(f"Content verification: {verification['status']}")
            
            # Get fresh content directly from documents
            retriever = get_real_time_retriever()
            fresh_results = retriever.retrieve_fresh_content(user_prompt, index_name, max_results=5)
            
            if not fresh_results:
                return {"error": f"No relevant content found in index '{index_name}'."}
            
            # Create context from fresh results
            context_text = "\n\n".join([
                f"Source: {result['source']}\nPage: {result.get('page', 'N/A')}\nContent: {result['content']}"
                for result in fresh_results
            ])
            
            # Create enhanced prompt with fresh context
            enhanced_prompt = f"""Based on the following fresh document content, please provide a comprehensive answer to the user's question.

User Question: {user_prompt}

Document Content:
{context_text}

Please provide a detailed, accurate response based solely on the document content above. Include specific references to pages and sections where relevant."""
            
            # Get LLM response with fresh context
            llm = get_chat_chain(context, retriever=None)
            response = llm.invoke(enhanced_prompt)
            
            # Format source documents for compatibility
            source_docs = []
            for result in fresh_results:
                source_docs.append({
                    'page_content': result['content'],
                    'metadata': {
                        'source': result['source'],
                        'page': result.get('page', 'N/A'),
                        'section': result.get('section', 'N/A'),
                        'timestamp': result.get('timestamp', 'N/A')
                    }
                })
            
            return {
                "result": response.content,
                "source_documents": source_docs,
                "verification_status": verification['status']
            }
    
    except Exception as e:
        print(f"Agent execution failed: {e}")
        return {"error": str(e)}

def get_vector_store(index_name):
    """Get vector store for the specified index"""
    persist_dir = f"vectors/{index_name}"
    return Chroma(persist_directory=persist_dir, embedding_function=get_embeddings())

def retrieve_documents(prompt: str, index_name: str, k=5) -> list:
    """Retrieve relevant documents with source metadata"""
    try:
        vector_store = get_vector_store(index_name)
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.5}
        )
        return retriever.get_relevant_documents(prompt)
    except Exception as e:
        print(f"Document retrieval failed: {e}")
        return []

def format_context_with_sources(docs) -> str:
    """Format documents with source citations"""
    context = ""
    for i, doc in enumerate(docs):
        source = doc.metadata.get('source', 'Unknown Document')
        page = doc.metadata.get('page', 'N/A')
        context += f"[[Source {i+1}]] {source} (Page {page}):\n{doc.page_content}\n\n"
    return context

def score_claude(prompt: str) -> float:
    """Score Claude model suitability for the prompt"""
    score = 0.5
    if "summarize" in prompt.lower(): 
        score += 0.4
    if "analyze" in prompt.lower(): 
        score += 0.3
    if "explain" in prompt.lower():
        score += 0.2
    return min(score, 1.0)

def score_gpt(prompt: str) -> float:
    """Score GPT model suitability for the prompt"""
    score = 0.5
    if "creative" in prompt.lower(): 
        score += 0.4
    if "write" in prompt.lower(): 
        score += 0.3
    if "generate" in prompt.lower():
        score += 0.2
    return min(score, 1.0)

def score_deepseek(prompt: str) -> float:
    """Score DeepSeek model suitability for the prompt"""
    score = 0.4
    if any(word in prompt.lower() for word in ["math", "calculate", "compute", "solve"]):
        score += 0.4
    if "code" in prompt.lower():
        score += 0.3
    return min(score, 1.0)

def score_anthropic(prompt: str) -> float:
    """Score Anthropic model suitability for the prompt"""
    score = 0.45
    if any(word in prompt.lower() for word in ["ethics", "safe", "responsible", "moral"]):
        score += 0.4
    if "reasoning" in prompt.lower():
        score += 0.3
    return min(score, 1.0)

def choose_provider(prompt: str, index_name: str = None, override: str = None) -> str:
    """Choose the best LLM provider based on prompt analysis"""
    if override:
        return override
    
    scores = {
        "claude": score_claude(prompt),
        "gpt": score_gpt(prompt),
        "deepseek": score_deepseek(prompt),
        "anthropic": score_anthropic(prompt)
    }

    print("Provider Scores:", scores)
    best_provider = max(scores, key=scores.get)
    print(f"Selected provider: {best_provider}")
    return best_provider

def generate_prompt(prompt: str, index_name: str) -> tuple:
    """Generate enhanced prompt with context and source citations"""
    try:
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
You are an expert analyst for document-based queries. Answer the question based ONLY on the following context.
Cite sources using [[Source #]] notation after relevant statements.
If context is insufficient, say "I couldn't find definitive information in the provided documents".

Context:
{context}

Question: {prompt}

Response Guidelines:
1. Answer in markdown format with clear sections
2. Always cite sources after key statements using [[Source #]] notation
3. Never speculate or invent information not in the context
4. Highlight key terms in **bold**
5. Include a "Sources" section at the end listing all references
6. Be concise but thorough in your analysis
"""

        return enhanced_prompt, sources
    
    except Exception as e:
        print(f"Prompt generation failed: {e}")
        return prompt, []
