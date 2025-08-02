from agents.writer_agent import WriterAgent

writer = WriterAgent()
response = writer.act(query="What is ingestion?", context_chunks=["Chunk 1 text", "Chunk 2 text"], provider="openai")

print(response)
