import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_deepseek import ChatDeepSeek
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from app.utils.index_utils import load_index
from langchain_community.llms import HuggingFacePipeline

print("✅ LangChain retrieval chain module loaded")

# Add utils directory to path
utils_path = Path(__file__).resolve().parent
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

def get_llm(provider: str) -> BaseChatModel:
    """Initialize the LLM based on the specified provider"""
    temperature = 0.3

    if provider == "openai":
        # Prevent older OpenAI SDKs from receiving unsupported 'project' kwarg
        try:
            os.environ.pop("OPENAI_PROJECT", None)
        except Exception:
            pass
        return ChatOpenAI(
            model="gpt-4",
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    if provider in ["claude", "anthropic"]:
        return ChatAnthropic(
            model="claude-3-7-sonnet-20250219",
            temperature=temperature,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    if provider in ["deepseek", "deepseek-chat"]:
        return ChatDeepSeek(
            model="deepseek-chat",
            temperature=temperature,
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
    
    if provider == "mistral":
        return ChatMistralAI(
            model="mistral-medium",
            temperature=temperature,
            api_key=os.getenv("MISTRAL_API_KEY")
        )
    
    # Fallback to OpenAI if provider is not recognized
    # Ensure env var is cleared in fallback as well
    try:
        os.environ.pop("OPENAI_PROJECT", None)
    except Exception:
        pass
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY")
    )

def get_chat_chain(provider: str, index_name: str) -> Runnable:
    """Create a chat chain with the specified provider and index"""
    # Initialize the LLM
    llm = get_llm(provider)
    
    # Load the index
    db = load_index(index_name)
    retriever = db.as_retriever()

    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Use the following context to answer the question."),
        ("human", "Context:\n{context}\n\nQuestion:\n{input}")
    ])

    # Create document processing chain
    combine_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=prompt
    )

    # Create retrieval chain
    retrieval_chain = create_retrieval_chain(
        retriever=retriever,
        combine_docs_chain=combine_chain
    )

    return retrieval_chain

# Optional local test when running this file directly
if __name__ == "__main__":
    provider = "openai"
    index_name = "enterprise_guide_index"
    user_query = "What are the benefits of AWS cloud architecture?"

    chain = get_chat_chain(provider, index_name)
    response = chain.invoke({"input": user_query})
    answer = response.get("answer", "[No answer returned]")
    print("Assistant:", answer)
