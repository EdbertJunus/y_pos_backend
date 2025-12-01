from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
from io import BytesIO
import os
import io
import logging
from datetime import datetime
from crud import init_db, insert_sales_record, get_all_files, get_file_record, upsert_sales_record
from utils.file_handler import save_uploaded_file, delete_file, fetch_file_bytes
from config import FILES_DIR

app = FastAPI()

# Initialize database (Supabase or SQLite)
try:
    init_db()
    logging.info("Database initialized successfully")
except Exception as e:
    logging.warning(f"Database initialization warning: {e}")


# -----------------------
# Upload and Save Sales File
# -----------------------

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI on Vercel!"}

# Example route that returns JSON or streams files
@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/sales/upload")
async def upload_sales_file(
    month: str = Form(...), 
    file: UploadFile = File(...)
    ):
    contents = await file.read()

    # Save the file as cleaned file
    cleaned_name = f"{month}_cleaned.xlsx"
    result = save_uploaded_file(contents, cleaned_name)

    # Extract URL from result dict (if Supabase returns dict)
    if isinstance(result, dict):
        saved_path = result.get("url") or cleaned_name
        if result.get("error"):
            raise HTTPException(500, f"File upload failed: {result['error']}")
    else:
        # Fallback for string path
        saved_path = result

    # Insert into Supabase PostgreSQL
    try:
        upsert_sales_record(month, cleaned_name, saved_path)
        logging.info(f"Uploaded sales file for month: {month}")
    except Exception as e:
        logging.error(f"Failed to save record to database: {e}")
        raise HTTPException(500, f"Database error: {e}")

    return {"status": "success", "filename": cleaned_name, "path": saved_path}


# -----------------------
# List All Uploaded Sales Files
# -----------------------
@app.get("/sales/list")
def list_sales_files():
    return get_all_files()


# -----------------------
# Download saved file by ID
# -----------------------
@app.get("/sales/download/{file_id}")
def download_file(file_id: int):
    record = get_file_record(file_id)
    if not record:
        raise HTTPException(404, "File not found")

    file_path = record["saved_path"]
    if not os.path.exists(file_path):
        raise HTTPException(404, "File missing on server")

    return FileResponse(
        file_path,
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/sales/all")
def get_all_sales_files():
    try:
        files = get_all_files()
        return [{"id": f.get("id"), "month": f.get("month"), "path": f.get("saved_path")} for f in files]
    except Exception as e:
        logging.error(f"Failed to fetch sales files: {e}")
        raise HTTPException(500, f"Database error: {e}")


# -----------------------
# Upload Single STOCK File (Only One)
# - When reuploaded, delete previous stock file
# -----------------------
@app.post("/stock/upload")
async def upload_stock_file(
    file: UploadFile = File(...)
    ):
    contents = await file.read()

    # use a fixed filename for the single stock file
    stock_name = "clean_stock.xlsx"

    # remove previous file if exists (handles both supabase and local)
    try:
        delete_file(stock_name)
    except Exception as e:
        logging.warning(f"Failed to delete previous stock file: {e}")

    result = save_uploaded_file(contents, stock_name)

    # Extract URL from result dict (if Supabase returns dict)
    if isinstance(result, dict):
        saved_path = result.get("url") or stock_name
        if result.get("error"):
            raise HTTPException(500, f"Stock file upload failed: {result['error']}")
    else:
        saved_path = result

    logging.info(f"Uploaded stock file: {stock_name}")
    return {"status": "success", "filename": stock_name, "path": saved_path}

def merge_data(stock_path_or_url):
    """
    Merge stock data with all sales files.
    stock_path_or_url can be a local path, HTTP URL, or Supabase URL.
    """
    # 1. Read the stock file
    try:
        stock_bytes = fetch_file_bytes(stock_path_or_url)
        stock_df = pd.read_excel(BytesIO(stock_bytes))
    except Exception as e:
        logging.error(f"Failed to read stock file: {e}")
        raise HTTPException(500, f"Failed to read stock file: {e}")

    # 2. Fetch ALL sales files metadata from Supabase
    try:
        sales_files = get_all_files()
    except Exception as e:
        logging.error(f"Failed to fetch sales files from database: {e}")
        raise HTTPException(500, f"Database error: {e}")

    merged_df = stock_df.copy()
    
    # 3. Loop all sales files
    for record in sales_files:
        month = record.get("month")
        path = record.get("saved_path")
        
        if not month or not path:
            logging.warning(f"Skipping invalid record: {record}")
            continue
            
        logging.info(f"Merging sales file for {month}: {path}")

        try:
            file_bytes = fetch_file_bytes(path)
            df_sales = pd.read_excel(BytesIO(file_bytes))
        except Exception as e:
            logging.warning(f"Failed to read {path}: {e}")
            continue

        if "Kode Item" not in df_sales.columns or "Jumlah" not in df_sales.columns:
            logging.warning(f"Invalid file format in {path}: missing required columns")
            continue

        merged_df = merged_df.merge(
            df_sales[["Kode Item", "Jumlah"]],
            on="Kode Item",
            how="left",
            suffixes=("", f"_{month}")
        )
        logging.info(f"Merged {month}")

        merged_df.rename(columns={"Jumlah": f"Sales_{month}"}, inplace=True)
        merged_df[f"Sales_{month}"] = merged_df[f"Sales_{month}"].fillna(0)
    
    # 4. Compute average
    qty_cols = [c for c in merged_df.columns if c.startswith("Sales_")]
    if qty_cols:
        merged_df["Average_Qty"] = merged_df[qty_cols].mean(axis=1)

    output_path = os.path.join(FILES_DIR, "stock_merged.xlsx")
    merged_df.to_excel(output_path, index=False)

    return merged_df, output_path

# Download Merged Stock with Sales
@app.get("/stock/download")
def download_stock_file():
    stock_name = "clean_stock.xlsx"
    
    try:
        # Try to fetch stock file bytes to verify it exists
        stock_bytes = fetch_file_bytes(stock_name)
    except FileNotFoundError:
        raise HTTPException(404, "Stock file not found. Please upload a stock file first.")
    except Exception as e:
        logging.error(f"Failed to fetch stock file: {e}")
        raise HTTPException(500, f"Error accessing stock file: {e}")

    try:
        merge_df, output_path = merge_data(stock_name)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Merge failed: {e}")
        raise HTTPException(500, f"Failed to merge files: {e}")

    # Check if merged file was created
    if not os.path.exists(output_path):
        raise HTTPException(500, "Failed to create merged file")

    today = datetime.now().strftime("%d-%m-%Y")
    stock_name_download = f"stock_{today}.xlsx"

    return FileResponse(
        output_path,
        filename=stock_name_download,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

