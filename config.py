import os
from dotenv import load_dotenv

# Load .env from project root (if present)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

DB_PATH = os.path.join(BASE_DIR, "database.db")
FILES_DIR = os.path.join(BASE_DIR, "saved_files")

# Supabase configuration (set these as environment variables or in .env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "pos-files")

# Enable supabase usage only if URL and KEY are provided
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

os.makedirs(FILES_DIR, exist_ok=True)  # Ensure local folder exists (fallback)
