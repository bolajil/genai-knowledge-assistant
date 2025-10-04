from agents.controller_agent import ControllerAgent

controller = ControllerAgent()

response = controller.run(
    query="What is ingestion?",
    index_name="test_index",
    top_k=5,
    provider="openai"
)

print(f"\n🎯 Agent Response:\n{response}\n")
