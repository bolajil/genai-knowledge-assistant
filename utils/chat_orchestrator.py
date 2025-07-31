import os
from dotenv import load_dotenv
load_dotenv()
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_deepseek import ChatDeepSeek  # or correct module path
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
#from query_helpers import load_index
from utils.query_helpers import load_index

print("✅ LangChain retrieval chain module loaded")


def get_llm(provider: str, index_name: str = None) -> BaseChatModel:
    temperature = 0.3

    if provider == "openai":
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
    elif provider == "mistral":
        return ChatMistralAI(
            model="mistral-medium",
            temperature=temperature,
            api_key=os.getenv("MISTRAL_API_KEY")
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_chat_chain(prompt: str, index_name: str, override: str = None) -> Runnable:
    provider = choose_provider(prompt, index_name, override)
    llm = get_llm(provider=provider, index_name=index_name)
    db = load_index(index_name)
    retriever = db.as_retriever()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Use the following context to answer the question."),
        ("human", "Context:\n{context}\n\nQuestion:\n{input}")
    ])

    combine_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=prompt
    )

    retrieval_chain = create_retrieval_chain(
        retriever=retriever,
        combine_docs_chain=combine_chain
    )

    return retrieval_chain  # ✅ return inside the function only

# ✅ Optional local test when running this file directly
if __name__ == "__main__":
    provider = "openai"
    index_name = "enterprise_guide_index"
    user_query = "What are the benefits of AWS cloud architecture?"

    chain = get_chat_chain(prompt=user_prompt, index_name=index_name)  # override optional
    response = chain.invoke({"input": user_prompt})
    print("Assistant:", response if isinstance(response, str) else response.get("answer", "[No answer returned]"))

