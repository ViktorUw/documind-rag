"""Ingestion: load documents -> split into chunks -> store in the vector database.

Run:  python -m app.ingest
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app import config
from app.store import get_collection, reset_collection

SUPPORTED = {".md", ".txt", ".pdf"}


@dataclass
class Chunk:
    text: str
    source: str   # file name
    section: str  # nearest markdown heading (or "" if none)

    @property
    def id(self) -> str:
        return hashlib.sha1(f"{self.source}|{self.section}|{self.text}".encode()).hexdigest()


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown by headings, so a chunk never mixes two topics.

    Returns a list of (heading, body). Text without headings becomes one section.
    """
    sections: list[tuple[str, str]] = []
    heading, buf = "", []
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)", line)
        if m:
            if "".join(buf).strip():
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        sections.append((heading, "\n".join(buf).strip()))
    return sections


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into pieces of at most `size` characters, with `overlap` characters
    repeated between neighbours so that a fact on a boundary is not lost.
    Tries to cut at a paragraph / sentence / word boundary."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    text = text.strip()
    pieces = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            for sep in ("\n\n", ". ", "\n", " "):
                cut = window.rfind(sep)
                if cut > size // 2:
                    end = start + cut + len(sep)
                    break
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [p for p in pieces if p]


def chunk_document(text: str, source: str) -> list[Chunk]:
    chunks = []
    for heading, body in split_sections(text):
        for piece in split_text(body, config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            chunks.append(Chunk(text=piece, source=source, section=heading))
    return chunks


def ingest(docs_dir: Path = config.DOCS_DIR) -> int:
    files = sorted(p for p in docs_dir.rglob("*") if p.suffix.lower() in SUPPORTED)
    if not files:
        raise SystemExit(f"No documents found in {docs_dir}")

    chunks: list[Chunk] = []
    for path in files:
        chunks.extend(chunk_document(load_text(path), source=path.name))

    # Deduplicate (identical chunks would give duplicate IDs).
    unique = {c.id: c for c in chunks}.values()

    collection = reset_collection()
    collection.add(
        ids=[c.id for c in unique],
        documents=[c.text for c in unique],
        metadatas=[{"source": c.source, "section": c.section} for c in unique],
    )
    print(f"Indexed {len(unique)} chunks from {len(files)} files.")
    return len(unique)


if __name__ == "__main__":
    ingest()
    print(f"Collection now holds {get_collection().count()} chunks.")
