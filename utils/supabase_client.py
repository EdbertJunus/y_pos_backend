import logging
import os
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET, USE_SUPABASE

supabase = None
bucket = SUPABASE_BUCKET

if USE_SUPABASE:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logging.warning(f"Failed to initialize Supabase client: {e}")
        supabase = None

__all__ = ["supabase", "bucket"]
