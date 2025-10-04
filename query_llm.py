from anthropic import Anthropic
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Avoid passing unsupported 'project' kwarg via environment to older SDKs
try:
    os.environ.pop("OPENAI_PROJECT", None)
except Exception:
    pass

openai_client = OpenAI(api_key=OPENAI_API_KEY)
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
claude_client = Anthropic(api_key=CLAUDE_API_KEY)

def synthesize_answer(query: str, chunks: List[str], provider: str = "openai") -> str:
    context = "\n\n".join(chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question.

Context:
{context}

Question:
{query}
"""

    try:
        if provider == "claude":
            response = claude_client.messages.create(
                model="claude-3-sonnet-20240229",  # or claude-3-sonnet
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        elif provider == "deepseek":
            response = deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=10
            )
            return response.choices[0].message.content.strip()

        else:  # OpenAI default
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=10
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        return f"[LLM Error] {str(e)}"
