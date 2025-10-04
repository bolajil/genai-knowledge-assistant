import os

base = "utils/models/all-MiniLM-L6-v2"
required_files = [
    "config.json", "modules.json", "tokenizer_config.json",
    "vocab.txt", "pytorch_model.bin"
]
pooling_config = os.path.join(base, "1_Pooling/config.json")

print("\n📦 Verifying model snapshot integrity:\n")
for f in required_files:
    path = os.path.join(base, f)
    print(f"{f:30}: {'✅' if os.path.isfile(path) else '❌'}")
print(f"{'1_Pooling/config.json':30}: {'✅' if os.path.isfile(pooling_config) else '❌'}")
