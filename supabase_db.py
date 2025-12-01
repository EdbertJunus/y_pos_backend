"""
Supabase PostgreSQL database connection and operations.
Uses supabase Python client for database access.
"""

import logging
from config import USE_SUPABASE, SUPABASE_URL, SUPABASE_KEY

supabase_client = None

if USE_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Supabase client initialized for database operations")
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
        supabase_client = None


def init_db():
    """Initialize the sales_files table in Supabase PostgreSQL."""
    if not supabase_client:
        logging.error("Supabase client not initialized")
        return

    try:
        # Create table if it doesn't exist
        sql = """
        CREATE TABLE IF NOT EXISTS public.sales_files (
            id BIGSERIAL PRIMARY KEY,
            month TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            saved_path TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create index on month for faster lookups
        CREATE INDEX IF NOT EXISTS idx_sales_files_month ON public.sales_files(month);
        """
        
        # Execute via Supabase REST API or use direct SQL
        # Since supabase-py doesn't have direct SQL execution for DDL,
        # we'll assume the table is created manually or use the SQL editor
        logging.info("Table creation SQL prepared (execute in Supabase SQL editor)")
        
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")


def upsert_sales_record(month: str, filename: str, saved_path: str):
    """Insert or update a sales record."""
    if not supabase_client:
        raise Exception("Supabase client not initialized")

    try:
        # Check if record exists
        existing = supabase_client.table("sales_files").select("id").eq("month", month).execute()
        
        if existing.data and len(existing.data) > 0:
            # Update existing record
            supabase_client.table("sales_files").update({
                "filename": filename,
                "saved_path": saved_path,
                "updated_at": "NOW()"
            }).eq("month", month).execute()
            logging.info(f"Updated sales record for month: {month}")
        else:
            # Insert new record
            supabase_client.table("sales_files").insert({
                "month": month,
                "filename": filename,
                "saved_path": saved_path
            }).execute()
            logging.info(f"Inserted new sales record for month: {month}")
            
    except Exception as e:
        logging.error(f"Failed to upsert sales record: {e}")
        raise


def get_all_files():
    """Get all sales files ordered by created_at descending."""
    if not supabase_client:
        raise Exception("Supabase client not initialized")

    try:
        response = supabase_client.table("sales_files").select("*").order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        logging.error(f"Failed to fetch all files: {e}")
        raise


def get_file_record(file_id: int):
    """Get a specific file record by ID."""
    if not supabase_client:
        raise Exception("Supabase client not initialized")

    try:
        response = supabase_client.table("sales_files").select("*").eq("id", file_id).execute()
        return response.data[0] if response.data and len(response.data) > 0 else None
    except Exception as e:
        logging.error(f"Failed to fetch file record: {e}")
        raise


def insert_sales_record(month, filename, saved_path):
    """Insert a new sales record (without checking for duplicates)."""
    if not supabase_client:
        raise Exception("Supabase client not initialized")

    try:
        supabase_client.table("sales_files").insert({
            "month": month,
            "filename": filename,
            "saved_path": saved_path
        }).execute()
        logging.info(f"Inserted sales record for month: {month}")
    except Exception as e:
        logging.error(f"Failed to insert sales record: {e}")
        raise

