"""Measure the quality of the RAG pipeline on a fixed set of questions.

Two levels:
  * retrieval  (free, no API calls): is the right document among the top-k chunks?
  * end-to-end (calls the LLM):      does the answer contain the expected fact,
                                      and does it cite the right document?

Questions with "expected_source": null have no answer in the docs; the assistant
should say it doesn't know instead of inventing something.

Run:
  python -m evals.run_evals --retrieval-only
  python -m evals.run_evals
"""

import argparse
import json
from pathlib import Path

from app import config
from app.store import search

QUESTIONS = Path(__file__).parent / "questions.jsonl"
NOT_FOUND_MARKERS = ("could not find", "couldn't find", "not contain", "no information", "not mentioned")


def load() -> list[dict]:
    return [json.loads(line) for line in QUESTIONS.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("-k", type=int, default=config.TOP_K)
    args = parser.parse_args()

    cases = load()
    retrieval_hits = answer_hits = cite_hits = answerable = 0

    for case in cases:
        q, expected = case["question"], case["expected_source"]
        sources = [c.source for c in search(q, k=args.k)]
        line = f"- {q[:60]:<60}"

        if expected:
            answerable += 1
            hit = expected in sources
            retrieval_hits += hit
            line += f" retrieval={'✓' if hit else '✗'}"

        if not args.retrieval_only:
            from app.rag import answer

            a = answer(q, k=args.k)
            text = a.text.lower()
            if expected:
                ok = all(s.lower() in text for s in case["must_contain"])
                cited = any(c.source == expected for c in a.citations)
            else:  # unanswerable: should admit it and not cite anything
                ok = any(m in text for m in NOT_FOUND_MARKERS) or not a.citations
                cited = not a.citations
            answer_hits += ok
            cite_hits += cited
            line += f" answer={'✓' if ok else '✗'} cited={'✓' if cited else '✗'}"
        print(line)

    print(f"\nRetrieval hit@{args.k}: {retrieval_hits}/{answerable} = {retrieval_hits / answerable:.0%}")
    if not args.retrieval_only:
        n = len(cases)
        print(f"Answer correct:     {answer_hits}/{n} = {answer_hits / n:.0%}")
        print(f"Correct citation:   {cite_hits}/{n} = {cite_hits / n:.0%}")


if __name__ == "__main__":
    main()
