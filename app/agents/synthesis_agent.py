from agents.base_agent import BaseAgent
from utils.query_llm import synthesize_answer

class SynthesisAgent(BaseAgent):
    def act(self, query: str, chunks: list, provider: str) -> str:
        self.observe(f"Synthesizing answer using {provider}")
        return synthesize_answer(query=query, chunks=chunks, provider=provider)
