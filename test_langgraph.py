from utils.langgraph_agent import build_graph
import langgraph.prebuilt as lg
graph = build_graph()
output = graph.invoke({"question": "What is LangGraph?"})
print(output["answer"])
print("✅ Available items in langgraph.prebuilt:")
print(dir(lg))
