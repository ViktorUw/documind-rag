"""Vector store (ChromaDB) and retrieval.

Chroma's default embedding function runs a small local model (all-MiniLM-L6-v2, ONNX),
so embeddings are free and need no extra API key.
"""

from dataclasses import dataclass

import chromadb

from app import config


@dataclass
class Retrieved:
    text: str
    source: str
    section: str
    distance: float  # cosine distance: lower = more similar


def _client() -> chromadb.ClientAPI:
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def get_collection():
    return _client().get_or_create_collection(
        config.COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def reset_collection():
    client = _client()
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:  # collection did not exist yet
        pass
    return get_collection()


def search(query: str, k: int = config.TOP_K) -> list[Retrieved]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    res = collection.query(query_texts=[query], n_results=min(k, collection.count()))
    return [
        Retrieved(text=doc, source=meta["source"], section=meta["section"], distance=dist)
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]
