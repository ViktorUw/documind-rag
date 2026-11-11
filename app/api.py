"""REST API.

Run:  uvicorn app.api:app --reload
Docs: http://localhost:8000/docs
"""

import os
import shutil

import anthropic
import openai
from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import config
from app.ingest import SUPPORTED, ingest
from app.rag import answer
from app.store import get_collection

app = FastAPI(
    title="DocuMind", description="Ask questions about your documents, with sources."
)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=config.TOP_K, ge=1, le=10)


class CitationOut(BaseModel):
    source: str
    section: str
    quote: str


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    retrieved_sources: list[str]
    model: str
    input_tokens: int
    output_tokens: int


@app.get("/health")
def health():
    return {"status": "ok", "chunks": get_collection().count()}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    key = (
        "ANTHROPIC_API_KEY" if config.LLM_PROVIDER == "anthropic" else "OPENAI_API_KEY"
    )
    if not os.getenv(key):
        raise HTTPException(500, f"{key} is not set (see .env.example)")
    try:
        a = answer(req.question, k=req.top_k)
    except (anthropic.AuthenticationError, openai.AuthenticationError):
        raise HTTPException(500, f"Invalid {key}")
    except (anthropic.RateLimitError, openai.RateLimitError):
        raise HTTPException(429, "Rate limited by the LLM API, try again shortly")
    except (anthropic.APIStatusError, openai.APIStatusError) as e:
        raise HTTPException(502, f"LLM API error: {e.message}")
    except (anthropic.APIConnectionError, openai.APIConnectionError):
        raise HTTPException(503, "Could not reach the LLM API")

    return AskResponse(
        answer=a.text,
        citations=[CitationOut(**c.__dict__) for c in a.citations],
        retrieved_sources=sorted({c.source for c in a.chunks}),
        model=a.model,
        input_tokens=a.input_tokens,
        output_tokens=a.output_tokens,
    )


@app.post("/documents")
def upload(file: UploadFile):
    """Upload a .md / .txt / .pdf file and re-index the knowledge base."""
    name = (file.filename or "").rsplit("/", 1)[-1]
    if not name or not any(name.lower().endswith(ext) for ext in SUPPORTED):
        raise HTTPException(
            400, f"Supported file types: {', '.join(sorted(SUPPORTED))}"
        )
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.DOCS_DIR / name, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"saved": name, "chunks": ingest()}


@app.get("/documents")
def list_documents():
    return sorted(
        p.name for p in config.DOCS_DIR.glob("*") if p.suffix.lower() in SUPPORTED
    )
