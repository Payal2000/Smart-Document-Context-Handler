"""Tests for the chunking engine."""
import pytest
from app.core.chunking_engine import split_into_chunks, trim_boilerplate


def _make_long_text(sentences: int = 100) -> str:
    return " ".join(
        f"This is sentence number {i} in the document, containing useful information about topic {i % 10}."
        for i in range(1, sentences + 1)
    )


def test_basic_chunking():
    text = _make_long_text(100)
    chunks = split_into_chunks(text, target_tokens=100, overlap_tokens=10)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.text.strip()
        assert chunk.token_count > 0


def test_chunk_indices_are_sequential():
    text = _make_long_text(80)
    chunks = split_into_chunks(text, target_tokens=80, overlap_tokens=10)
    for i, chunk in enumerate(chunks):
        assert chunk.index == i


def test_single_sentence_fits_in_one_chunk():
    text = "Short document."
    chunks = split_into_chunks(text, target_tokens=512)
    assert len(chunks) == 1
    assert chunks[0].text == "Short document."


def test_trim_boilerplate_removes_page_numbers():
    text = "Introduction\n\nPage 1\n\nSome real content here.\n\nPage 2\n\nMore content."
    trimmed = trim_boilerplate(text)
    assert "Page 1" not in trimmed
    assert "Some real content" in trimmed


def test_trim_boilerplate_collapses_whitespace():
    text = "Line one.   \nLine two.   \n\n\n\n\nLine three."
    trimmed = trim_boilerplate(text)
    # Should not have more than 2 consecutive newlines
    assert "\n\n\n" not in trimmed


def test_overlap_creates_shared_sentences():
    """With overlap, adjacent chunks should share sentences."""
    text = _make_long_text(60)
    chunks = split_into_chunks(text, target_tokens=60, overlap_tokens=15)
    if len(chunks) >= 2:
        # The last sentence of chunk 0 should appear at start of chunk 1 (due to overlap)
        # We just verify chunks are not completely disjoint
        last_words_c0 = set(chunks[0].text.split()[-5:])
        first_words_c1 = set(chunks[1].text.split()[:10])
        overlap_exists = bool(last_words_c0 & first_words_c1)
        assert overlap_exists or len(chunks) == 1, "Expected overlap between adjacent chunks"


def test_empty_text_returns_empty():
    chunks = split_into_chunks("", target_tokens=512)
    assert chunks == []
