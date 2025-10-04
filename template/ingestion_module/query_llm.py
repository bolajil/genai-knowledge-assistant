from typing import List
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4"

# Prevent older SDKs from receiving unsupported 'project' kwarg via env
try:
    os.environ.pop("OPENAI_PROJECT", None)
except Exception:
    pass

client = OpenAI(api_key=OPENAI_API_KEY)

def synthesize_answer(query: str, chunks: List[str], provider: str = "openai") -> str:
    context = "\n\n".join(chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question.

Context:
{context}

Question:
{query}
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=10
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM Error] {str(e)}"
