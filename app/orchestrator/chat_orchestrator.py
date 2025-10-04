
#New update here

import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema.runnable import Runnable
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_deepseek import ChatDeepSeek  # or correct module path
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from app.utils.index_utils import load_index  # Or your existing loader
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.documents import Document
from utils.query_helpers import load_index
from typing import List, Dict, Any
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence

print("✅ LangChain retrieval chain module loaded")


def get_llm(provider: str) -> BaseChatModel:
    temperature = 0.3

    if provider == "openai":
        # Prevent older OpenAI SDKs from receiving unsupported 'project' kwarg
        try:
            os.environ.pop("OPENAI_PROJECT", None)
        except Exception:
            pass
        return ChatOpenAI(
            model="gpt-4-turbo",
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    elif provider in ["claude", "anthropic"]:
        return ChatAnthropic(
            model="claude-3-7-sonnet-20250219",
            temperature=temperature,
            api_key=os.getenv("ANTHROPIC_API_KEY")
       )

    elif provider in ["deepseek", "deepseek-chat"]:
        return ChatDeepSeek(
            model="deepseek-chat",
            temperature=temperature,
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
    elif provider == "mistral":
        return ChatMistralAI(
            model="mistral-medium",
            temperature=temperature,
            api_key=os.getenv("MISTRAL_API_KEY")
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

from langchain_core.runnables import Runnable
from langchain.prompts import ChatPromptTemplate
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document  # Or langchain.schema
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from typing import List, Dict, Any
from langchain_core.output_parsers import StrOutputParser


def get_chat_chain(provider: str, index_name: str) -> Runnable:
    llm = get_llm(provider)
    db = load_index(index_name)
    print(f"🔍 Loaded index: {index_name}")
    print(f" DB object type: {type(db)}")
    retriever = db.as_retriever()
    print(f"🔍 Retriever object: {retriever}")
    print(f"📌 Invoking chain on index: {index_name}")



    prompt = ChatPromptTemplate.from_messages([
        ("system", "You're a cloud security expert. Use the retrieved context to produce a thorough, structured answer."),
        ("human", "Context:\n{context}\n\nQuestion:\n{input}")
    ])

    # Input normalization layer
    def normalize_input(input_data: Any) -> Dict[str, Any]:
        """Handle all possible input formats"""
        if isinstance(input_data, str):
            return {"input": input_data}
        elif isinstance(input_data, dict):
            # Extract from common keys
            for key in ["input", "query", "question"]:
                if key in input_data:
                    return {"input": str(input_data[key])}
            # Fallback to string conversion
            return {"input": str(input_data)}
        else:
            return {"input": str(input_data)}

    # Safe context formatting
    def format_context(docs: List[Document]) -> str:
        if not docs:
            return "[No context retrieved]"
        return "\n\n".join(getattr(doc, "page_coitent", str(doc)) for doc in docs)
    # Build the chain with pipe operators instead of .then()
    chain = (
        RunnableLambda(normalize_input)
        | RunnablePassthrough.assign(
            context=lambda x: format_context(retriever.invoke(x["input"]))
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


# ✅ Optional local test when running this file directly
if __name__ == "__main__":
    provider = "openai"
    index_name = "enterprise_guide_index"
    user_query = "What are the benefits of AWS cloud architecture?"

    chain = get_chat_chain(provider="openai", index_name=index_name)
    response = chain.invoke({"query": user_prompt})
    print("Assistant:", response if isinstance(response, str) else response.get("answer", "[No answer returned]"))
    print("Expected input keys:", chain.input_schema.schema())

