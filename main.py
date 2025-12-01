from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
from io import BytesIO
import os
import io
from datetime import datetime
from crud import init_db, insert_sales_record, get_all_files, get_file_record, upsert_sales_record
from utils.file_handler import save_uploaded_file
from config import FILES_DIR

app = FastAPI()
init_db()


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
    saved_path = save_uploaded_file(contents, cleaned_name)

    # Insert into SQLite
    # upsert_sales_record(month, cleaned_name, saved_path)

    return {"status": "success", "filename": cleaned_name}


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
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute("SELECT month, saved_path FROM sales_files").fetchall()
    conn.close()

    return [{"month": r["month"], "path": r["saved_path"]} for r in rows]


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
    stock_path = os.path.join(FILES_DIR, stock_name)

    # remove previous file if exists (handles both supabase and local)
    try:
        from utils.file_handler import delete_file
        delete_file(stock_name)
    except Exception:
        # non-fatal: continue and attempt upload
        pass

    saved_path = save_uploaded_file(contents, stock_name)

    return {"status": "success", "filename": stock_name}

def merge_data(stock_path):
    # 1. Read the stock file
    stock_df = pd.read_excel(stock_path)

    # 2. Fetch ALL sales files metadata from backend database
    sales_files = get_all_files()  
    # or requests.get(...) if you really call your own API
    # but better to read DB directly internally

    merged_df = stock_df.copy()
    
    # 3. Loop all sales files
    for record in sales_files:
        month = record["month"]
        path = record["saved_path"]
        print(month, path)

        try:
            df_sales = pd.read_excel(path)
        except Exception as e:
            print(f"Failed to read {path}: {e}")
            continue

        if "Kode Item" not in df_sales.columns or "Jumlah" not in df_sales.columns:
            print(f"Invalid file format: {path}")
            continue

        merged_df = merged_df.merge(
            df_sales[["Kode Item", "Jumlah"]],
            on="Kode Item",
            how="left",
            suffixes=("", f"_{month}")
        )
        print(month)
        # print(merged_df.head(10))

        merged_df.rename(columns={"Jumlah": f"Sales_{month}"}, inplace=True)
        merged_df[f"Sales_{month}"] = merged_df[f"Sales_{month}"].fillna(0)
        # print(merged_df.head(10))
    # 4. Compute average
    qty_cols = [c for c in merged_df.columns if c.startswith("Sales_")]
    merged_df["Average_Qty"] = merged_df[qty_cols].mean(axis=1)

    output_path = os.path.join(FILES_DIR, "stock_merged.xlsx")
    
    merged_df.to_excel(output_path, index=False)

    return merged_df, output_path

# Download Merged Stock with Sales
@app.get("/stock/download")
def download_stock_file():
    today = datetime.now().strftime("%d-%m-%Y")
    stock_name = f"stock_{today}.xlsx"
    stock_path = os.path.join(FILES_DIR, "stock.xlsx")

    merge_df, output_path = merge_data(stock_path)
    

    if not os.path.exists(stock_path):
        raise HTTPException(404, "Stock file not found")

    if not os.path.exists(output_path):
        raise HTTPException(404, "Merged file not found")

    return FileResponse(
        output_path,
        filename=stock_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

