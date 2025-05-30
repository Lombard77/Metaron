
import os
import zipfile

print("Working dir:", os.getcwd())
print("Running script file:", __file__)

# === USER CONFIGURATION ===
SOURCE_DIR = r'C:\MyDevProjects\Metatron'
OUTPUT_ZIP = r'C:\MyDevProjects\Metatron\filtered_project.zip'

# File extensions to include
INCLUDE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.json',
    '.html', '.css', '.txt', '.md', '.yml', '.yaml',
    '.csv', '.env', '.toml'
}

# Directory names to exclude
EXCLUDE_DIRS = {
    'node_modules', '.git', '.venv', 'venv', '__pycache__',
    'dist', 'build', '.idea', '.vscode', '.mypy_cache',
    'site-packages', 'vector_store'
}

# File extensions to exclude
EXCLUDE_EXTENSIONS = {
    '.exe', '.dll', '.zip', '.tar', '.gz', '.db', '.log', '.sqlite', '.jpg', '.png', '.heic'
}


def should_include_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    return ext in INCLUDE_EXTENSIONS and ext not in EXCLUDE_EXTENSIONS


def should_exclude_dir(dirname):
    return any(excluded in dirname for excluded in EXCLUDE_DIRS)


def zip_filtered_project(source_dir, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude unwanted dirs
            dirs[:] = [d for d in dirs if not should_exclude_dir(os.path.join(root, d))]
            
            for file in files:
                filepath = os.path.join(root, file)
                if should_include_file(filepath):
                    arcname = os.path.relpath(filepath, source_dir)
                    zipf.write(filepath, arcname)
                    print(f"Included: {arcname}")

    print(f"\n✅ Done! Zip created at: {output_zip}")


if __name__ == "__main__":
    zip_filtered_project(SOURCE_DIR, OUTPUT_ZIP)
