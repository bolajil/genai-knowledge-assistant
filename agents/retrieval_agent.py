from agents.base_agent import BaseAgent
from utils.query_helpers import query_index

class RetrievalAgent(BaseAgent):
    def act(self, query: str, index_name: str, top_k: int) -> list:
        self.observe("Retrieve top-k chunks from FAISS")
        return query_index(query=query, index_name=index_name, top_k=top_k)
