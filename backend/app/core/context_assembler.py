"""
Context Assembler — packages the final prompt based on the processing tier.

Given a document and a query, applies the appropriate tier strategy and
returns the assembled context string + metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from .budget_allocator import TokenBudget, allocate
from .chunking_engine import Chunk, Chunk, split_into_chunks, trim_boilerplate
from .rag_pipeline import RAGPipeline, RetrievedChunk, bm25_rank_chunks
from .tier_classifier import Tier, TierResult
from .token_estimator import count_tokens, truncate_to_tokens


@dataclass
class AssembledContext:
    tier: Tier
    assembled_text: str
    token_count: int
    budget: TokenBudget
    chunks_used: list[dict] = field(default_factory=list)   # for T3/T4
    strategy_notes: str = ""


def assemble(
    raw_text: str,
    tier_result: TierResult,
    query: Optional[str] = None,
    rag_pipeline: Optional[RAGPipeline] = None,
    top_k: int = 10,
) -> AssembledContext:
    """
    Main entry point. Returns an AssembledContext for the given tier.
    """
    tier = tier_result.tier

    if tier == Tier.T1:
        return _assemble_t1(raw_text, tier_result)

    elif tier == Tier.T2:
        return _assemble_t2(raw_text, tier_result)

    elif tier == Tier.T3:
        return _assemble_t3(raw_text, tier_result, query or "", top_k)

    elif tier == Tier.T4:
        return _assemble_t4(raw_text, tier_result, query or "", rag_pipeline, top_k)

    raise ValueError(f"Unknown tier: {tier}")


# ------------------------------------------------------------------
# Tier 1 — Direct injection
# ------------------------------------------------------------------

def _assemble_t1(raw_text: str, tier_result: TierResult) -> AssembledContext:
    token_count = count_tokens(raw_text)
    budget = allocate(token_count)
    # Safety truncation (shouldn't be needed for T1, but just in case)
    text = truncate_to_tokens(raw_text, budget.document_max)

    logger.info(f"T1 assembly: {token_count:,} tokens, no processing")
    return AssembledContext(
        tier=Tier.T1,
        assembled_text=text,
        token_count=count_tokens(text),
        budget=budget,
        strategy_notes="Full document injected without modification.",
    )


# ------------------------------------------------------------------
# Tier 2 — Smart trimming
# ------------------------------------------------------------------

def _assemble_t2(raw_text: str, tier_result: TierResult) -> AssembledContext:
    original_tokens = count_tokens(raw_text)
    trimmed = trim_boilerplate(raw_text)
    trimmed_tokens = count_tokens(trimmed)
    budget = allocate(trimmed_tokens)
    text = truncate_to_tokens(trimmed, budget.document_max)
    final_tokens = count_tokens(text)

    saved = original_tokens - final_tokens
    logger.info(f"T2 assembly: {original_tokens:,} → {final_tokens:,} tokens (saved {saved:,})")
    return AssembledContext(
        tier=Tier.T2,
        assembled_text=text,
        token_count=final_tokens,
        budget=budget,
        strategy_notes=(
            f"Boilerplate removed. Tokens reduced from {original_tokens:,} to {final_tokens:,} "
            f"(saved {saved:,} tokens)."
        ),
    )


# ------------------------------------------------------------------
# Tier 3 — Strategic chunking + BM25 ranking
# ------------------------------------------------------------------

def _assemble_t3(
    raw_text: str,
    tier_result: TierResult,
    query: str,
    top_k: int,
) -> AssembledContext:
    from .budget_allocator import DOCUMENT_MAX

    chunks = split_into_chunks(raw_text, target_tokens=512, overlap_tokens=50)

    if query.strip():
        ranked = bm25_rank_chunks(chunks, query, top_k=min(top_k * 2, len(chunks)))
    else:
        # No query: return first N chunks that fit budget
        ranked = [
            type("RC", (), {"chunk": c, "score": 1.0, "rank": i + 1})()
            for i, c in enumerate(chunks)
        ]

    # Greedy fill within document budget
    selected_chunks: list[RetrievedChunk] = []
    used_tokens = 0
    for rc in ranked:
        if used_tokens + rc.chunk.token_count > DOCUMENT_MAX:
            break
        selected_chunks.append(rc)
        used_tokens += rc.chunk.token_count

    # Sort selected chunks back into document order
    selected_chunks.sort(key=lambda rc: rc.chunk.index)

    assembled = "\n\n---\n\n".join(rc.chunk.text for rc in selected_chunks)
    budget = allocate(used_tokens)

    logger.info(f"T3 assembly: {len(chunks)} chunks → {len(selected_chunks)} selected, {used_tokens:,} tokens")
    return AssembledContext(
        tier=Tier.T3,
        assembled_text=assembled,
        token_count=used_tokens,
        budget=budget,
        chunks_used=[
            {"index": rc.chunk.index, "tokens": rc.chunk.token_count, "score": round(rc.score, 4)}
            for rc in selected_chunks
        ],
        strategy_notes=(
            f"Document split into {len(chunks)} chunks. "
            f"Top {len(selected_chunks)} selected via BM25 ranking ({used_tokens:,} tokens)."
        ),
    )


# ------------------------------------------------------------------
# Tier 4 — RAG retrieval
# ------------------------------------------------------------------

def _assemble_t4(
    raw_text: str,
    tier_result: TierResult,
    query: str,
    rag_pipeline: Optional[RAGPipeline],
    top_k: int,
) -> AssembledContext:
    from .budget_allocator import DOCUMENT_MAX

    if rag_pipeline is None:
        # Build a fresh pipeline from the raw text
        chunks = split_into_chunks(raw_text, target_tokens=512, overlap_tokens=50)
        rag_pipeline = RAGPipeline()
        rag_pipeline.build_index(chunks)

    if query.strip():
        retrieved = rag_pipeline.retrieve(query, top_k=top_k)
    else:
        # No query: return first top_k chunks
        retrieved = [
            RetrievedChunk(chunk=c, score=1.0, rank=i + 1)
            for i, c in enumerate(rag_pipeline._chunks[:top_k])
        ]

    # Sort by document order
    retrieved.sort(key=lambda rc: rc.chunk.index)

    # Greedy fill
    selected: list[RetrievedChunk] = []
    used_tokens = 0
    for rc in retrieved:
        if used_tokens + rc.chunk.token_count > DOCUMENT_MAX:
            break
        selected.append(rc)
        used_tokens += rc.chunk.token_count

    assembled = "\n\n---\n\n".join(rc.chunk.text for rc in selected)
    budget = allocate(used_tokens)

    logger.info(f"T4 assembly: retrieved {len(retrieved)} → {len(selected)} chunks, {used_tokens:,} tokens")
    return AssembledContext(
        tier=Tier.T4,
        assembled_text=assembled,
        token_count=used_tokens,
        budget=budget,
        chunks_used=[
            {"index": rc.chunk.index, "tokens": rc.chunk.token_count, "score": round(rc.score, 4)}
            for rc in selected
        ],
        strategy_notes=(
            f"Vector similarity search retrieved {len(retrieved)} chunks. "
            f"{len(selected)} fit within token budget ({used_tokens:,} tokens)."
        ),
    )
