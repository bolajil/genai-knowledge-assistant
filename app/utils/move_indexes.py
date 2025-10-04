from pathlib import Path
import shutil

def move_index(source_path, target_root="data/faiss_index"):
    target_path = Path(target_root) / source_path.name
    target_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Moving {source_path} to {target_path}")
    shutil.copytree(source_path, target_path, dirs_exist_ok=True)

if __name__ == "__main__":
    # Move your specific index
    move_index(Path("vectorstores/compliance_demo"))
    
    # Add any other indexes that need moving
    # move_index(Path("another/path"))
