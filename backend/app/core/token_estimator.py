"""
Token Estimator — exact token counts using tiktoken (cl100k_base).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from loguru import logger


@lru_cache(maxsize=1)
def _get_encoding():
    """Cache the tiktoken encoder (loading it once is expensive)."""
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        raise ImportError("tiktoken not installed. Run: pip install tiktoken")


def count_tokens(text: str) -> int:
    """Return the exact token count for a string using cl100k_base encoding."""
    if not text:
        return 0
    enc = _get_encoding()
    return len(enc.encode(text))


def estimate_tokens_from_bytes(byte_size: int) -> int:
    """
    Fast heuristic: ~4 bytes per token for English text.
    Use this for quick pre-screening before full encode.
    """
    return byte_size // 4


def count_tokens_batch(texts: list[str]) -> list[int]:
    """Count tokens for a list of strings efficiently."""
    enc = _get_encoding()
    return [len(enc.encode(t)) for t in texts]


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to at most max_tokens tokens, preserving whole tokens."""
    if not text:
        return text
    enc = _get_encoding()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    logger.debug(f"Truncating from {len(tokens)} to {max_tokens} tokens")
    return enc.decode(tokens[:max_tokens])
