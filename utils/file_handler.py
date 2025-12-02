import os
import logging
from io import BytesIO
import requests

from config import FILES_DIR, USE_SUPABASE
from utils.supabase_client import supabase, bucket as SUPABASE_BUCKET


def save_uploaded_file(upload_file: bytes, save_name: str) -> str:
    """
    Save the uploaded file. If Supabase is configured, upload to Supabase Storage
    and return the public URL. Otherwise write to local `FILES_DIR` and return the path.
    """
    # Try supabase upload first
    if USE_SUPABASE and supabase:
        object_path = save_name
        try:
            # remove existing object if present to allow overwrite
            try:
                supabase.storage.from_(SUPABASE_BUCKET).remove([object_path])
            except Exception:
                pass

            # upload bytes
            try:
                supabase.storage.from_(SUPABASE_BUCKET).upload(object_path, upload_file)
            except Exception as e:
                logging.warning(f"Supabase upload error: {e}")
                raise

            public = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(object_path)
           
            if isinstance(public, dict):
                public_url = public.get("publicURL") or public.get("public_url")
            else:
                public_url = str(public)

            # ALWAYS RETURN JSON
            return {"url": public_url, "error": None}
        except Exception as e:
            logging.warning(f"Supabase upload failed, falling back to local. Error: {e}")
            return {"url": None, "error": str(e)}
    # # Fallback: save locally
  
    return {"url": None, "error": "Supabase not configured"}

def delete_file(save_name: str) -> bool:
    """Delete file from Supabase if configured else from local storage.
    Returns True if deleted or didn't exist, False on failure.
    """
    if USE_SUPABASE and supabase:
        try:
            supabase.storage.from_(SUPABASE_BUCKET).remove([save_name])
            return True
        except Exception as e:
            logging.warning(f"Failed to delete from Supabase: {e}")
            return False

    # local delete
    file_path = os.path.join(FILES_DIR, save_name)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except OSError as e:
            logging.warning(f"Failed to delete local file {file_path}: {e}")
            return False
    return True

def extract_object_path(saved_url: str) -> str:
    return saved_url.split("/pos-files/", 1)[-1]


def fetch_file_bytes(path_or_url: str) -> bytes:
    """Given either a local path or an HTTP URL, return bytes of the file."""
    # HTTP URL

    path_or_url = extract_object_path(path_or_url)

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        print("Fetching via HTTP:", path_or_url, flush=True)
        try:
            r = requests.get(path_or_url)
            r.raise_for_status()
            return r.content
        except Exception as e:
            raise FileNotFoundError(f"Failed to download file via URL: {e}")

    
    if USE_SUPABASE and supabase:
        # object_name = path_or_url.split("/", 1)[-1]
        print(f"Fetching from Supabase: {path_or_url}", flush=True)
        try:
            file_obj = supabase.storage.from_(SUPABASE_BUCKET).download(path_or_url)
            
            # new fix — extract bytes properly
            if hasattr(file_obj, "data"):
                return file_obj.data  
            if isinstance(file_obj, bytes):
                return file_obj

            return BytesIO(file_obj).getvalue()

        except Exception as e:
            raise FileNotFoundError(f"Unable to fetch file from Supabase: {e}")


    raise FileNotFoundError(f"File not found locally or as URL: {path_or_url}")

