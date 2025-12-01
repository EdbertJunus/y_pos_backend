"""
CRUD operations using Supabase PostgreSQL.
Replaces SQLite operations with Supabase REST API calls.
"""

import logging
from config import USE_SUPABASE

if USE_SUPABASE:
    from supabase_db import (
        init_db,
        insert_sales_record,
        get_all_files,
        get_file_record,
        upsert_sales_record
    )
else:
    # Fallback to SQLite if Supabase is not configured
    logging.warning("Supabase not configured, operations may fail. Please configure SUPABASE_URL and SUPABASE_KEY")
    from database import get_db
    
    def init_db():
        from models import CREATE_SALES_TABLE
        conn = get_db()
        conn.execute(CREATE_SALES_TABLE)
        conn.commit()
        conn.close()

    def insert_sales_record(month, filename, saved_path):
        conn = get_db()
        conn.execute("""
            INSERT INTO sales_files (month, filename, saved_path)
            VALUES (?, ?, ?)
        """, (month, filename, saved_path))
        conn.commit()
        conn.close()

    def get_all_files():
        conn = get_db()
        rows = conn.execute("SELECT * FROM sales_files ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_file_record(file_id):
        conn = get_db()
        row = conn.execute("SELECT * FROM sales_files WHERE id = ?", (file_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def upsert_sales_record(month: str, filename: str, saved_path: str):
        conn = get_db()
        cursor = conn.cursor()

        # Check if the month already exists
        existing = cursor.execute(
            "SELECT id FROM sales_files WHERE month = ?",
            (month,)
        ).fetchone()

        if existing:
            # Update the existing row
            cursor.execute("""
                UPDATE sales_files
                SET filename = ?, saved_path = ?, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (filename, saved_path, existing["id"]))
        else:
            # Insert a new row
            cursor.execute("""
                INSERT INTO sales_files (month, filename, saved_path)
                VALUES (?, ?, ?)
            """, (month, filename, saved_path))

        conn.commit()
        conn.close()

