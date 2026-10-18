# Autonomous Enterprise Document Agent

**Python · FastAPI · React · LLMs · Pydantic · MySQL**

An autonomous agent that reads freight invoices and bills of lading, extracts structured data with an LLM, reconciles it against purchase orders in a database, and routes exceptions to a human reviewer through a web dashboard.

## What it does

1. **Deterministic extraction.** A Pydantic model is the single source of truth: it generates the JSON schema sent to the LLM (temperature 0, schema-enforced output) and strictly validates the response. It pulls PO numbers, line items and financial totals from unstructured PDFs.
2. **Autonomous validation engine.** A FastAPI workflow parses, extracts, asserts, reconciles and routes each document. Extracted totals are reconciled against PO records in MySQL, with tolerance-based exception flagging (default 1%).
3. **Human-in-the-loop dashboard.** A React dashboard shows the original PDF beside extracted-vs-PO values, highlights discrepancies and schema validation failures, and lets operators approve, reject or re-run documents.
4. **Fallback handling.** Parsing and extraction failures are handled in layers:
   - Text layer first, OCR fallback for scanned PDFs.
   - Post-extraction assertions catch hallucinations: the PO number and total must appear in the document text, and quantity x price = amount, lines + tax = total.
   - Failed checks retry with error feedback, then fall back to a rule-based extractor.
   - If everything fails, the document is routed to a human as `SCHEMA_FAILED` with a full audit trail.

## Document routing

| Status | Meaning |
|---|---|
| `AUTO_APPROVED` | Matches the PO within tolerance, no human needed |
| `FLAGGED` | Discrepancy against the PO, needs review |
| `SCHEMA_FAILED` | Extraction failed validation, needs review |
| `APPROVED` / `REJECTED` | Final human decision |

## Project structure

```
backend/
  app/
    main.py              FastAPI app
    schemas.py           Pydantic extraction schema (single source of truth)
    models.py            SQLAlchemy tables
    services/
      pdf_parser.py      PyMuPDF text layer + OCR fallback
      extractor.py       Gemini call, retries, rule-based fallback
      validator.py       Hallucination and arithmetic assertions
      reconciler.py      PO matching + tolerance flagging
      workflow.py        End-to-end orchestration
    routers/documents.py Upload, list, review endpoints
    seed.py              8 mock purchase orders
  make_samples.py        Generates 8 test PDFs
frontend/                React + Tailwind (Vite) review dashboard
```

## Setup

### 1. Database
Create an empty MySQL database (MySQL Workbench or CLI):
```sql
CREATE DATABASE IF NOT EXISTS docagent CHARACTER SET utf8mb4;
```

### 2. Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
```
Edit `.env`: set your MySQL password in `DATABASE_URL` (URL-encode special characters, e.g. `@` becomes `%40`) and optionally your Gemini key.

```bash
python -m app.seed                # create tables + 8 mock POs
python make_samples.py            # generate sample PDFs in ./samples
python -m uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## LLM configuration

Without an API key the app runs on the rule-based extractor. To use Gemini, create a free key at https://aistudio.google.com/apikey and set it in `backend/.env`:
```
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.5-flash-lite
```
Notes: model names change over time (list the ones your key can use with the Google GenAI SDK), and the free tier has a small daily request limit. When Gemini is unavailable or rate-limited, the fallback chain keeps documents flowing.

## Try it

Upload all 8 files from `backend/samples/`. Expected results:

| File | Result |
|---|---|
| 1 matching invoice | Auto-approved |
| 2 overcharged invoice (+8%) | Flagged |
| 3 unknown PO number | Flagged |
| 4 matching bill of lading | Auto-approved |
| 5 bill of lading, wrong weight | Flagged |
| 6 invoice with no total | Schema failed |
| 7 total does not match line items | Schema failed |
| 8 scanned image-only PDF | Auto-approved via OCR (needs Tesseract) |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/documents/upload` | Upload and process a PDF |
| GET | `/documents?status=` | List documents |
| GET | `/documents/{id}` | Detail with expected PO |
| GET | `/documents/{id}/file` | Original PDF |
| POST | `/documents/{id}/approve` or `/reject` | Reviewer decision |
| POST | `/documents/{id}/reprocess` | Re-run extraction |
| GET | `/stats`, `/purchase-orders` | Dashboard data |

## Optional: OCR
Install Tesseract (`brew install tesseract` on macOS) to enable OCR for scanned PDFs.