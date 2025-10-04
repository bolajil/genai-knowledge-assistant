from agents.base_agent import BaseAgent

class ReasoningAgent(BaseAgent):
    def act(self, query: str) -> str:
        self.observe("Break query into reasoning steps")
        # For now, return simplified plan
        return f"Step 1: Retrieve context\nStep 2: Synthesize answer to '{query}'"
