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
            supabase.storage.from_(SUPABASE_BUCKET).upload(object_path, upload_file)

            public = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(object_path)
            # supabase client returns dict with 'publicURL' or similar
            public_url = None
            if isinstance(public, dict):
                public_url = public.get("publicURL") or public.get("public_url")
            elif hasattr(public, "get"):
                public_url = public.get("publicURL")

            return public_url or f"{SUPABASE_BUCKET}/{object_path}"
        except Exception as e:
            logging.warning(f"Supabase upload failed, falling back to local. Error: {e}")

    # Fallback: save locally
    file_path = os.path.join(FILES_DIR, save_name)
    with open(file_path, "wb") as f:
        f.write(upload_file)
    return file_path


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


def fetch_file_bytes(path_or_url: str) -> bytes:
    """Given either a local path or an HTTP URL, return bytes of the file."""
    # HTTP URL
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        r = requests.get(path_or_url)
        r.raise_for_status()
        return r.content

    # local path
    if os.path.exists(path_or_url):
        with open(path_or_url, "rb") as f:
            return f.read()

    # If it's of the form 'bucket/object' and supabase available, try download
    if USE_SUPABASE and supabase and "/" in path_or_url:
        # assume format 'object_name' or 'bucket/object'
        object_name = path_or_url.split("/", 1)[-1]
        try:
            data = supabase.storage.from_(SUPABASE_BUCKET).download(object_name)
            # Some clients return a file-like or bytes
            if isinstance(data, bytes):
                return data
            # otherwise turn into bytes
            return BytesIO(data).getvalue()
        except Exception as e:
            raise FileNotFoundError(f"Unable to fetch file from Supabase: {e}")

    raise FileNotFoundError(f"File not found locally or as URL: {path_or_url}")

