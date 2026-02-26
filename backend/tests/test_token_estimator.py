"""Tests for token estimation."""
import pytest
from app.core.token_estimator import (
    count_tokens,
    count_tokens_batch,
    estimate_tokens_from_bytes,
    truncate_to_tokens,
)


def test_empty_string():
    assert count_tokens("") == 0


def test_known_count():
    # "Hello world" is reliably 2-3 tokens
    count = count_tokens("Hello world")
    assert 2 <= count <= 3


def test_batch_matches_individual():
    texts = ["Hello world", "This is a test.", "Another sentence here."]
    batch = count_tokens_batch(texts)
    individual = [count_tokens(t) for t in texts]
    assert batch == individual


def test_truncate_does_not_exceed_limit():
    text = " ".join(["word"] * 500)
    truncated = truncate_to_tokens(text, max_tokens=100)
    assert count_tokens(truncated) <= 100


def test_truncate_short_text_unchanged():
    text = "Short text."
    result = truncate_to_tokens(text, max_tokens=100)
    assert result == text


def test_estimate_from_bytes_heuristic():
    # 4000 bytes ~ 1000 tokens
    est = estimate_tokens_from_bytes(4000)
    assert est == 1000
