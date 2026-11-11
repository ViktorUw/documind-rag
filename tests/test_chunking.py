import pytest

from app.ingest import chunk_document, split_sections, split_text


def test_split_sections_uses_headings():
    text = "# Title\nintro\n\n## A\nalpha text\n\n## B\nbeta text"
    assert split_sections(text) == [("Title", "intro"), ("A", "alpha text"), ("B", "beta text")]


def test_text_without_headings_is_one_section():
    assert split_sections("just some text") == [("", "just some text")]


def test_split_text_respects_size_and_covers_everything():
    text = " ".join(f"word{i}" for i in range(500))
    pieces = split_text(text, size=200, overlap=50)
    assert len(pieces) > 1
    assert all(len(p) <= 200 for p in pieces)
    for i in (0, 250, 499):  # every word appears in some chunk
        assert any(f"word{i}" in p for p in pieces)


def test_split_text_has_overlap():
    text = ". ".join(f"Sentence number {i}" for i in range(100))
    a, b = split_text(text, size=300, overlap=100)[:2]
    assert a[-30:].split()[-1] in b  # end of chunk 1 is repeated at the start of chunk 2


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        split_text("abc", size=10, overlap=10)


def test_chunks_keep_source_and_section():
    chunks = chunk_document("# Leave\nYou get 26 days.", source="policy.md")
    assert chunks[0].source == "policy.md"
    assert chunks[0].section == "Leave"
    assert "26 days" in chunks[0].text


def test_quote_check_ignores_case_whitespace_and_trailing_dot():
    from app.rag import _normalize

    chunk = "Every full-time employee receives 26 working days\nof paid vacation per calendar year."
    assert _normalize("every full-time employee receives 26 working days of paid vacation") in _normalize(chunk)
    assert _normalize("employees receive 30 days") not in _normalize(chunk)
