import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
FILES_DIR = os.path.join(BASE_DIR, "saved_files")

os.makedirs(FILES_DIR, exist_ok=True)  # Ensure folder exists
