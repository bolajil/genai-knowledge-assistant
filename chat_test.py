from dotenv import load_dotenv
load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

from utils.query_helpers import load_index
from utils.chat_orchestrator import get_llm

provider = "openai"
index_name = "Rackspace-Ebook-6-benefits-public-cloud-master-AWS-12639_index"
query_text = "What are the key benefits of AWS cloud architecture?"

llm = get_llm(provider)
db = load_index(index_name)
retriever = db.as_retriever()

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "Context:\n{context}\n\nQuestion:\n{input}")
])

# ✅ Step 1: Build document combine chain
combine_chain = create_stuff_documents_chain(
    llm=llm,
    prompt=prompt
)

# ✅ Step 2: Build full retrieval + response chain
retrieval_chain = create_retrieval_chain(
    retriever=retriever,
    combine_docs_chain=combine_chain,
    #input_key="query"
)

# ✅ Step 3: Run query
response = retrieval_chain.invoke({"input":  query_text})

# ✅ Step 4: Print response
print("Assistant:", response if isinstance(response, str) else response.get("answer", "[No answer returned]"))
