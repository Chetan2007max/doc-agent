from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import documents

app = FastAPI(title="Autonomous Enterprise Document Agent")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(documents.router)


@app.on_event("startup")
def _startup():
    Base.metadata.create_all(engine)


@app.get("/health")
def health():
    provider = "gemini" if (settings.gemini_api_key and settings.llm_provider != "heuristic") else "rule_based"
    return {"status": "ok", "extractor": provider, "tolerance_pct": settings.tolerance_pct}
