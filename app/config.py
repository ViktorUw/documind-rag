"""Central settings, read from environment variables (or a .env file)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

DOCS_DIR = Path(os.getenv("DOCS_DIR", ROOT / "data" / "docs"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / "data" / "chroma"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "docs")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()  # "openai" or "anthropic"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "medium")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))       # characters
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))  # characters
TOP_K = int(os.getenv("TOP_K", "4"))
