# scripts/ingest/ingest_csv.py

import os
import sys
from pathlib import Path
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from utils.weaviate_manager import get_weaviate_manager

DATA_PATH = Path("data")
BATCH_SIZE = 100  # Optimal batch size for Weaviate

def select_csv():
    csv_files = list(DATA_PATH.glob("*.csv"))
    if not csv_files:
        print("❌ No CSV files found in /data")
        return None

    print("📂 Available CSV files:")
    for i, f in enumerate(csv_files):
        print(f"[{i}] {f.name}")

    choice = input("Select file by number: ").strip()
    if not choice.isdigit() or int(choice) >= len(csv_files):
        print("⚠️ Invalid selection.")
        return None

    return csv_files[int(choice)]

def ingest_csv(file_path: Path):
    try:
        # Read CSV with chunking for large files
        df = pd.read_csv(file_path)
        wm = get_weaviate_manager()
        index_name = f"{file_path.stem}_index"
        
        # Initialize progress bar
        total_rows = len(df)
        pbar = tqdm(total=total_rows, desc="Ingesting rows")
        
        # Batch processing
        batch = []
        for idx, row in df.iterrows():
            batch.append({
                "content": " | ".join(f"{col}: {row[col]}" for col in df.columns),
                "source": file_path.name,
                "source_type": "csv",
                "metadata": {"row_index": idx}
            })
            
            if len(batch) >= BATCH_SIZE:
                wm.add_documents(index_name, batch)
                pbar.update(len(batch))
                batch = []
        
        # Process final batch
        if batch:
            wm.add_documents(index_name, batch)
            pbar.update(len(batch))
            
        pbar.close()
        print(f"✅ Successfully ingested {total_rows} rows into '{index_name}'")
        
    except Exception as e:
        print(f"❌ Ingestion failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    file_path = select_csv()
    if file_path:
        ingest_csv(file_path)
