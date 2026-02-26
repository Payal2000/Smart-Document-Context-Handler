"""
Chunking Engine — sentence-aware and section-aware document splitting.

Strategy:
  1. Section splitting: detect markdown headers and double-newline paragraph breaks
  2. Sentence splitting: use NLTK punkt tokenizer within each section
  3. Merge short sentences into chunks of target_tokens with overlap
  4. Tier-2 trimming: remove boilerplate patterns (ToC, headers/footers)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from .token_estimator import count_tokens, count_tokens_batch

# Patterns that indicate boilerplate content (for Tier 2 trimming)
_BOILERPLATE_PATTERNS = [
    re.compile(r"^(table of contents|contents|index)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^page \d+\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*\d+\s*$", re.MULTILINE),                  # bare page numbers
    re.compile(r"^(header|footer|copyright|all rights reserved).*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^[-=_*]{5,}\s*$", re.MULTILINE),              # horizontal rules
    re.compile(r"\n{3,}", re.MULTILINE),                        # excessive blank lines → double newline
]

# Section header pattern (markdown ## style or ALL CAPS lines)
_SECTION_HEADER = re.compile(
    r"^(#{1,6}\s+.+|[A-Z][A-Z\s]{4,}[A-Z])$",
    re.MULTILINE
)


@dataclass
class Chunk:
    index: int
    text: str
    token_count: int
    section_header: Optional[str] = None
    start_char: int = 0
    end_char: int = 0


def trim_boilerplate(text: str) -> str:
    """
    Tier-2 strategy: remove common boilerplate and compress whitespace.
    Returns cleaned text.
    """
    for pattern in _BOILERPLATE_PATTERNS:
        if pattern.pattern == r"\n{3,}":
            text = pattern.sub("\n\n", text)
        else:
            text = pattern.sub("", text)

    # Collapse multiple spaces (but not newlines)
    text = re.sub(r"[ \t]+", " ", text)
    # Remove trailing spaces on each line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = text.strip()
    logger.debug(f"Boilerplate trim: {len(text):,} chars remaining")
    return text


def split_into_chunks(
    text: str,
    target_tokens: int = 512,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """
    Split text into semantic chunks using NLTK sentence tokenizer.
    Falls back to paragraph splitting if NLTK is unavailable.
    """
    sentences = _sentence_tokenize(text)
    if not sentences:
        return []

    sentence_tokens = count_tokens_batch(sentences)
    chunks: list[Chunk] = []
    current_sentences: list[str] = []
    current_tokens = 0
    chunk_idx = 0
    char_offset = 0

    for sent, tok_count in zip(sentences, sentence_tokens):
        # If a single sentence exceeds target, emit it alone
        if tok_count > target_tokens and not current_sentences:
            start = text.find(sent, char_offset)
            chunks.append(Chunk(
                index=chunk_idx,
                text=sent,
                token_count=tok_count,
                start_char=start,
                end_char=start + len(sent),
            ))
            chunk_idx += 1
            char_offset = start + len(sent)
            continue

        if current_tokens + tok_count > target_tokens and current_sentences:
            chunk_text = " ".join(current_sentences)
            start = text.find(current_sentences[0], char_offset)
            chunks.append(Chunk(
                index=chunk_idx,
                text=chunk_text,
                token_count=current_tokens,
                start_char=start,
                end_char=start + len(chunk_text),
            ))
            chunk_idx += 1

            # Overlap: keep last N tokens worth of sentences
            overlap_sents, overlap_toks = _get_overlap_sentences(
                current_sentences, sentence_tokens, overlap_tokens
            )
            current_sentences = overlap_sents
            current_tokens = overlap_toks
            char_offset = start + len(chunk_text)

        current_sentences.append(sent)
        current_tokens += tok_count

    # Flush remaining
    if current_sentences:
        chunk_text = " ".join(current_sentences)
        start = text.find(current_sentences[0], char_offset)
        chunks.append(Chunk(
            index=chunk_idx,
            text=chunk_text,
            token_count=current_tokens,
            start_char=max(0, start),
            end_char=max(0, start) + len(chunk_text),
        ))

    logger.info(f"Chunking: {len(sentences)} sentences → {len(chunks)} chunks "
                f"(target={target_tokens} tokens, overlap={overlap_tokens})")
    return chunks


def _sentence_tokenize(text: str) -> list[str]:
    """Tokenize text into sentences using NLTK punkt, with paragraph fallback."""
    try:
        import nltk
        try:
            tokenizer = nltk.data.load("tokenizers/punkt_tab/english.pickle")
        except (LookupError, OSError):
            try:
                tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
            except (LookupError, OSError):
                nltk.download("punkt", quiet=True)
                nltk.download("punkt_tab", quiet=True)
                try:
                    tokenizer = nltk.data.load("tokenizers/punkt_tab/english.pickle")
                except (LookupError, OSError):
                    tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
        sentences = tokenizer.tokenize(text)
        return [s.strip() for s in sentences if s.strip()]
    except Exception as e:
        logger.warning(f"NLTK tokenizer failed ({e}), falling back to paragraph split")
        return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]


def _get_overlap_sentences(
    sentences: list[str],
    token_counts: list[int],
    overlap_tokens: int,
) -> tuple[list[str], int]:
    """Return the trailing sentences that together fit within overlap_tokens."""
    overlap_sents = []
    overlap_toks = 0
    for sent, toks in zip(reversed(sentences), reversed(token_counts)):
        if overlap_toks + toks > overlap_tokens:
            break
        overlap_sents.insert(0, sent)
        overlap_toks += toks
    return overlap_sents, overlap_toks
