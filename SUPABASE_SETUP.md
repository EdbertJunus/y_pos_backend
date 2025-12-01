# Supabase PostgreSQL Migration Guide

This guide walks you through setting up Supabase PostgreSQL to replace SQLite for your POS backend.

## Step 1: Create or Use Existing Supabase Project

1. Go to https://app.supabase.com
2. Sign in or create account
3. Create a new project or select existing one
4. Wait for the project to initialize (2-3 minutes)

## Step 2: Get Database Credentials

Navigate to **Settings → Database** in your Supabase project:

1. You'll see a section "Connection Info"
2. Copy the following:
   - **Host**: Your database host
   - **Port**: Usually 5432 (PostgreSQL default)
   - **Database**: Usually "postgres"
   - **User**: Usually "postgres"
   - **Password**: Your database password (click to reveal)

**Example connection string:**

```
postgresql://postgres:YOUR_PASSWORD@db.xxxxxxxxxxxx.supabase.co:5432/postgres
```

## Step 3: Get API Credentials

Navigate to **Settings → API** in your Supabase project:

1. Copy **Project URL** (e.g., `https://xxxxxxxxxxxx.supabase.co`)
2. Copy **Service Role Key** (under "API Keys" → "Service role secret") — use this for server-side operations

⚠️ **Important:** Keep the service role key secret. Do NOT expose it in frontend code or public repos.

## Step 4: Create the sales_files Table

Go to **SQL Editor** in your Supabase dashboard and run this SQL:

```sql
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

-- Enable Row Level Security (optional, for future access control)
ALTER TABLE public.sales_files ENABLE ROW LEVEL SECURITY;
```

## Step 5: Set Environment Variables

Update your `.env` file (or Vercel environment variables for production):

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...YOUR_SERVICE_ROLE_KEY
SUPABASE_BUCKET=pos-files
SUPABASE_DB_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxxxxxxxxx.supabase.co:5432/postgres
```

**Or locally (PowerShell):**

```powershell
$env:SUPABASE_URL = 'https://xxxxxxxxxxxx.supabase.co'
$env:SUPABASE_KEY = 'your_service_role_key_here'
$env:SUPABASE_BUCKET = 'pos-files'
$env:SUPABASE_DB_URL = 'postgresql://postgres:password@db.xxxxxxxxxxxx.supabase.co:5432/postgres'
```

## Step 6: Install Dependencies

```powershell
pip install -r requirements.txt
```

**Key new packages:**

- `supabase` — Supabase Python SDK
- `psycopg2-binary` — PostgreSQL database adapter

## Step 7: For Vercel Deployment

1. Go to your Vercel project settings
2. Navigate to **Environment Variables**
3. Add the four variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (service role)
   - `SUPABASE_BUCKET`
   - `SUPABASE_DB_URL` (optional, but recommended for direct Postgres access)

## Step 8: Test the Setup

1. Start the backend locally:

   ```powershell
   uvicorn main:app --reload --port 8000
   ```

2. Upload a sales file via `/sales/upload`:

   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/sales/upload" `
     -Method Post `
     -Form @{ month = "2025-01"; file = Get-Item "C:\path\to\sales.xlsx" }
   ```

3. Check if the record appears in Supabase SQL Editor:

   ```sql
   SELECT * FROM public.sales_files;
   ```

4. List sales files via API:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/sales/list"
   ```

## Troubleshooting

### Error: "Supabase client not initialized"

- **Cause:** `SUPABASE_URL` or `SUPABASE_KEY` not set in environment
- **Fix:** Double-check `.env` file or environment variables, restart app

### Error: "relation \"sales_files\" does not exist"

- **Cause:** Table not created in Supabase
- **Fix:** Run the SQL from Step 4 in Supabase SQL Editor

### Error: "UNIQUE constraint violated"

- **Cause:** Trying to insert a month that already exists
- **Fix:** Use `upsert_sales_record()` instead of `insert_sales_record()` (already handled in `/sales/upload`)

### Error: "permission denied for schema public"

- **Cause:** Service role key missing RLS bypass or incorrect permissions
- **Fix:** Use the **Service Role Key** (not anon key) and verify it has full table permissions

### Files upload successfully but database query fails

- **Cause:** Supabase Storage and PostgreSQL are separate services; check both configs
- **Fix:** Verify `SUPABASE_KEY` has Storage AND Database permissions

## Key Files Changed

- **`supabase_db.py`** (new) — Supabase PostgreSQL CRUD operations
- **`config.py`** — Added `SUPABASE_DB_URL` and `SUPABASE_URL/SUPABASE_KEY` config
- **`crud.py`** — Refactored to use Supabase (with SQLite fallback)
- **`main.py`** — Updated endpoints to handle dict/string returns from file upload and use logging
- **`requirements.txt`** — Added `supabase` and `psycopg2-binary`
- **`.env.example`** — Updated with Supabase database URL variable

## Architecture Overview

```
Frontend (React/Vue/etc.)
    ↓
FastAPI Backend (main.py)
    ├── /sales/upload → save_uploaded_file() → Supabase Storage
    │                → upsert_sales_record() → Supabase PostgreSQL
    │
    ├── /sales/list → get_all_files() → Supabase PostgreSQL
    │
    └── /stock/download → merge_data() → reads from Supabase Storage + PostgreSQL
```

## Next Steps (Optional Enhancements)

1. **Add Row Level Security (RLS)** to control which users can access which records
2. **Implement authentication** (JWT tokens) for API endpoints
3. **Add migrations** for schema changes using Alembic
4. **Enable backup policies** in Supabase Settings → Backups

---

**Questions?** Check Supabase docs: https://supabase.com/docs
