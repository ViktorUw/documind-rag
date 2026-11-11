"""RAG: retrieve relevant chunks, then ask an LLM to answer using only those chunks.

Two providers are supported (set LLM_PROVIDER in .env):
  * openai    - chunks are numbered in the prompt; the model returns JSON with the answer
                and quotes, and every quote is checked against the chunk text so that
                invented citations are dropped.
  * anthropic - chunks are sent as `document` blocks with Claude's Citations API, which
                returns exact quotes tied to the chunk they came from.
"""

import json
from dataclasses import dataclass, field

from app import config
from app.store import Retrieved, search

SYSTEM_PROMPT = """You are an internal knowledge-base assistant for a company.
Answer the user's question using ONLY the provided documents.
If the documents do not contain the answer, say clearly that you could not find it
in the knowledge base, and do not guess.
Answer in the same language as the question. Be concise and specific."""

OPENAI_FORMAT = """
Reply with a JSON object of this shape:
{"answer": "<answer, with [n] markers after claims>",
 "citations": [{"doc": <document number n>, "quote": "<exact sentence copied from that document>"}]}
Quotes must be copied word for word from the documents. Use an empty list if nothing was found."""


@dataclass
class Citation:
    source: str
    section: str
    quote: str


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    chunks: list[Retrieved] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


def answer(question: str, k: int = config.TOP_K) -> Answer:
    chunks = search(question, k=k)
    if not chunks:
        return Answer(text="The knowledge base is empty. Run `python -m app.ingest` first.")
    if config.LLM_PROVIDER == "anthropic":
        a = _ask_claude(question, chunks)
    else:
        a = _ask_openai(question, chunks)
    a.chunks = chunks
    return a


# ---------------------------------------------------------------- OpenAI

_openai = None


def _ask_openai(question: str, chunks: list[Retrieved]) -> Answer:
    global _openai
    if _openai is None:
        from openai import OpenAI

        _openai = OpenAI()  # reads OPENAI_API_KEY from the environment

    docs = "\n\n".join(
        f'<document n="{i}" title="{c.source} — {c.section}">\n{c.text}\n</document>'
        for i, c in enumerate(chunks, 1)
    )
    response = _openai.chat.completions.create(
        model=config.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + OPENAI_FORMAT},
            {"role": "user", "content": f"{docs}\n\nQuestion: {question}"},
        ],
    )

    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"answer": raw, "citations": []}

    citations = []
    for c in data.get("citations") or []:
        try:
            chunk = chunks[int(c["doc"]) - 1]
        except (KeyError, ValueError, TypeError, IndexError):
            continue
        quote = str(c.get("quote", "")).strip()
        if quote and _normalize(quote) in _normalize(chunk.text):  # drop invented quotes
            citations.append(Citation(chunk.source, chunk.section, quote))

    usage = response.usage
    return Answer(
        text=str(data.get("answer", "")).strip(),
        citations=citations,
        model=response.model,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


def _normalize(s: str) -> str:
    return " ".join(s.lower().replace("**", "").split()).rstrip(".")


# ---------------------------------------------------------------- Anthropic (Claude)

_anthropic = None


def _ask_claude(question: str, chunks: list[Retrieved]) -> Answer:
    global _anthropic
    if _anthropic is None:
        import anthropic

        _anthropic = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    documents = [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": c.text},
            "title": f"{c.source} — {c.section}" if c.section else c.source,
            "citations": {"enabled": True},
        }
        for c in chunks
    ]
    response = _anthropic.beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        output_config={"effort": config.CLAUDE_EFFORT},
        # If a safety classifier declines, the API retries on a recommended fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": [*documents, {"type": "text", "text": question}]}],
    )

    if response.stop_reason == "refusal":
        return Answer(text="Sorry, I can't answer that question.")

    text_parts: list[str] = []
    citations: list[Citation] = []
    for block in response.content:
        if block.type != "text":
            continue  # skip thinking / fallback blocks
        text_parts.append(block.text)
        for cit in block.citations or []:
            src = chunks[cit.document_index]
            citations.append(Citation(src.source, src.section, cit.cited_text.strip()))
            text_parts.append(f" [{len(citations)}]")

    return Answer(
        text="".join(text_parts).strip(),
        citations=citations,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "How many vacation days do employees get?"
    a = answer(q)
    print(a.text, "\n")
    for i, c in enumerate(a.citations, 1):
        print(f"[{i}] {c.source} / {c.section}: \"{c.quote}\"")
    print(f"\n({a.model}, {a.input_tokens} in / {a.output_tokens} out tokens)")
