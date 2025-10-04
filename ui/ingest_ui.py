import streamlit as st
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# === Config ===
INDEX_ROOT = Path("data/faiss_index/")
EMBED_MODEL = "utils/models/all-MiniLM-L6-v2"

st.set_page_config(page_title="📡 PDF Query Assistant", page_icon="📘", layout="centered")
st.title("📘 PDF Query Assistant")
st.caption("Search embedded documents with semantic precision. Choose a document, ask a question, and explore AI-powered answers.")

# === Doc Selection
index_dirs = sorted([d.name for d in INDEX_ROOT.iterdir() if d.is_dir()])
selected_doc = st.selectbox("📂 Select a document to query", index_dirs, help="Choose from available embedded indexes")

# === Query Interface
question = st.text_input("📝 Enter your question", placeholder="e.g. What are the cloud security best practices?")
top_k = st.slider("🔢 Number of results", min_value=1, max_value=5, value=3)

# === Trigger Search
if selected_doc and question:
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db_path = INDEX_ROOT / selected_doc

    with st.spinner("🔍 Searching document..."):
        db = FAISS.load_local(str(db_path), embeddings, allow_dangerous_deserialization=True)
        results = db.similarity_search(question, k=top_k)

    st.success(f"✅ Top {top_k} semantic results from `{selected_doc}`")

    # === Display Results
    for i, doc in enumerate(results, 1):
        st.markdown(f"### 📌 Result {i}")
        st.write(doc.page_content[:600].strip() + "...")
        with st.expander("🔍 Full Context", expanded=False):
            st.code(doc.page_content.strip(), language="markdown")

    # === Optional: Show vector metadata later if needed
