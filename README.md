# Autonomous Enterprise Document Agent
Python · FastAPI · React · LLMs · Pydantic · MySQL

| Resume bullet | Where it lives |
|---|---|
| Deterministic extraction, JSON-schema enforcement | `schemas.py` (Pydantic = schema sent to LLM + validator), `services/extractor.py` (temperature 0, `response_schema`) |
| FastAPI validation engine, reconciliation, tolerance flagging | `services/workflow.py`, `services/reconciler.py` (`TOLERANCE_PCT`) |
| Human-in-the-loop React dashboard | `frontend/` (next step) + API: `/documents`, `/documents/{id}/file`, `/approve`, `/reject` |
| OCR/parsing fallbacks, hallucination mitigation | `services/pdf_parser.py` (text layer -> OCR), `services/validator.py` (grounding + arithmetic assertions), retry-with-feedback -> rule-based fallback -> `SCHEMA_FAILED` routing |

## Run (backend)
```bash
cd backend
python -m venv venv && venv\Scripts\activate        # Windows  (source venv/bin/activate on mac/linux)
pip install -r requirements.txt
copy .env.example .env                               # edit DATABASE_URL password
```
In MySQL Workbench run: `CREATE DATABASE docagent;`
```bash
python -m app.seed            # 8 mock POs   (--reset to reseed)
python make_samples.py        # 8 test PDFs in ./samples
uvicorn app.main:app --reload # http://localhost:8000/docs
```
Upload PDFs from `samples/` via the Swagger UI at `/docs`.

## Add Gemini (free)
Get a key at https://aistudio.google.com/apikey -> put it in `.env` as `GEMINI_API_KEY`. No other change needed.
Without a key, the rule-based extractor is used (same schema, same assertions).

## Optional OCR
Install Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) for scanned PDFs.
