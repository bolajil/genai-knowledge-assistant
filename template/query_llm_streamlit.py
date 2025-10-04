import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from typing import List
from openai import OpenAI

# === Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INDEX_ROOT = Path("data/faiss_index/")
EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"
OPENAI_MODEL = "gpt-4"
DEFAULT_K = 5

st.set_page_config(page_title="🧠 GenAI LLM Assistant", page_icon="📘", layout="centered")
st.title("🧠 GenAI LLM Assistant")
st.caption("Select a document, ask a question, and receive an intelligent answer using embedded context + LLM.")

index_dirs = sorted([d.name for d in INDEX_ROOT.iterdir() if d.is_dir()])
selected_doc = st.selectbox("📂 Choose a document index", index_dirs)

question = st.text_input("💬 Your question", placeholder="e.g. What are the benefits of AWS public cloud?")
top_k = st.slider("🔢 Number of chunks", min_value=1, max_value=10, value=DEFAULT_K)

if selected_doc and question:
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db_path = INDEX_ROOT / selected_doc

    with st.spinner("🔍 Searching for context..."):
        db = FAISS.load_local(str(db_path), embeddings, allow_dangerous_deserialization=True)
        results = db.similarity_search(question, k=top_k)
        chunks = [doc.page_content.strip() for doc in results]
        context = "\n\n".join(chunks)

    with st.spinner("🤖 Generating LLM-powered answer..."):
        # Prevent older SDKs from receiving unsupported 'project' kwarg via env
        try:
            os.environ.pop("OPENAI_PROJECT", None)
        except Exception:
            pass
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""
You are a helpful AI assistant. Based on the document excerpts below, provide a clear and concise answer to the user's question.

Document Chunks:
{context}

Question:
{question}

Answer:"""
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()
        st.success("✅ Answer generated")

        st.markdown("### 🧠 Answer")
        st.write(answer)

        with st.expander("📄 Show Retrieved Chunks", expanded=False):
            for i, chunk in enumerate(chunks, 1):
                st.markdown(f"**Chunk {i}:**\n{chunk[:800]}...")
