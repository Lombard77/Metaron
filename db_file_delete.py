from pathlib import Path
import shutil

vector_root = Path("data/vector_store")

if not vector_root.exists():
    print("⚠️ vector_store directory does not exist — nothing to delete.")
else:
    for folder in vector_root.iterdir():
        if folder.is_dir():
            print(f"🗑️ Deleting folder: {folder}")
            shutil.rmtree(folder)

    print("✅ All vectorstore folders deleted")
