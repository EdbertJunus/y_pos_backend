from database import get_db
from models import CREATE_SALES_TABLE

def init_db():
    conn = get_db()
    conn.execute(CREATE_SALES_TABLE)
    conn.commit()

def insert_sales_record(month, filename, saved_path):
    conn = get_db()
    conn.execute("""
        INSERT INTO sales_files (month, filename, saved_path)
        VALUES (?, ?, ?)
    """, (month, filename, saved_path))
    conn.commit()

def get_all_files():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sales_files ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]

def get_file_record(file_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM sales_files WHERE id = ?", (file_id,)).fetchone()
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
