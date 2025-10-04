import weaviate

client = weaviate.Client(
    url="https://f7ddaf12-85b7-42ec-861c-277c79c30a77.weaviate.network",
    auth_client_secret=weaviate.AuthApiKey(api_key="your-api-key-here")
)
print("Connection successful!" if client.is_ready() else "Connection failed")
