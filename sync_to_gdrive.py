import os
import shutil
from datetime import datetime

SOURCE_DIR = r"C:\MyDevProjects\Metatron"
DEST_DIR = r"G:\My Drive\Personal\My Dev Projects\MetatronBackupFromC"
LOG_FILE = os.path.join(SOURCE_DIR, "last_sync.log")

# Directory names to exclude
EXCLUDE_DIRS = {
    'node_modules', '.git', '.venv', 'venv', '__pycache__',
    'dist', 'build', '.idea', '.vscode', '.mypy_cache',
    'site-packages', 'vector_store'
}

def log(message):
    timestamp = datetime.now().isoformat(timespec='seconds')
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(formatted + "\n")

def should_copy(src_path, dest_path):
    if not os.path.exists(dest_path):
        return True

    if os.path.getsize(src_path) != os.path.getsize(dest_path):
        return True

    if os.path.getmtime(src_path) > os.path.getmtime(dest_path):
        return True

    return False

def sync_folder(src, dest):
    total_processed = 0
    total_copied = 0
    total_skipped = 0
    total_errors = 0

    for root, dirs, files in os.walk(src):
        # Exclude unwanted directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        rel_path = os.path.relpath(root, src)
        dest_root = os.path.join(dest, rel_path)
        os.makedirs(dest_root, exist_ok=True)

        for file in files:
            total_processed += 1
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_root, file)

            try:
                if should_copy(src_file, dest_file):
                    shutil.copy2(src_file, dest_file)
                    log(f"Copied: {os.path.relpath(src_file, src)}")
                    total_copied += 1
                else:
                    log(f"Skipped (up-to-date): {os.path.relpath(src_file, src)}")
                    total_skipped += 1
            except Exception as e:
                log(f"ERROR copying {src_file} -> {dest_file}: {e}")
                total_errors += 1

            if total_processed % 100 == 0:
                log(f"[progress] Processed: {total_processed} files...")

    return total_processed, total_copied, total_skipped, total_errors

def main():
    start = datetime.now()
    log(f"=== Sync started ===")
    processed, copied, skipped, errors = sync_folder(SOURCE_DIR, DEST_DIR)
    end = datetime.now()
    duration = (end - start).total_seconds()
    log(f"✔️ Sync finished in {duration:.2f} sec | Processed: {processed} | Copied: {copied} | Skipped: {skipped} | Errors: {errors}")

if __name__ == "__main__":
    main()
