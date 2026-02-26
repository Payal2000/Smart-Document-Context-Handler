"""
Query endpoint — assembles context for a document + query using the appropriate tier strategy.

POST /api/query
"""
from __future__ import annotations

import os
import pickle

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...config import get_settings
from ...core import (
    RAGPipeline,
    TierResult,
    allocate,
    assemble,
    budget_as_dict,
    classify,
    load_document,
    split_into_chunks,
)
from ...core.tier_classifier import Tier
from ...db.database import get_db
from ...db.models import Document
from ...models.document import ChunkInfo, QueryRequest, QueryResponse, TokenBudgetResponse

router = APIRouter(prefix="/query", tags=["query"])
settings = get_settings()

# In-memory cache: doc_id → RAGPipeline (for T4 documents within same process)
_rag_cache: dict[str, RAGPipeline] = {}


@router.post("/", response_model=QueryResponse)
async def query_document(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Given a doc_id and query, apply the tier-appropriate strategy and return
    the assembled context window content.
    """
    # Fetch document metadata
    result = await db.execute(select(Document).where(Document.id == request.doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {request.doc_id} not found")

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=410,
            detail="Document file no longer available. Please re-upload."
        )

    # Re-load raw text from disk
    with open(doc.file_path, "rb") as f:
        file_bytes = f.read()

    try:
        loaded = load_document(file_bytes, doc.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to re-parse document: {e}")

    tier = Tier(doc.tier)
    tier_result = TierResult(
        tier=tier,
        token_count=doc.token_count,
        label=doc.tier_label,
        color="#000000",
        description="",
    )

    # For T4, get or build RAG pipeline
    rag_pipeline = None
    if tier == Tier.T4:
        rag_pipeline = _get_or_build_rag(request.doc_id, loaded.raw_text)

    # Assemble context
    ctx = assemble(
        raw_text=loaded.raw_text,
        tier_result=tier_result,
        query=request.query,
        rag_pipeline=rag_pipeline,
        top_k=request.top_k,
    )

    return QueryResponse(
        doc_id=request.doc_id,
        query=request.query,
        tier=tier.value,
        assembled_context=ctx.assembled_text,
        token_count=ctx.token_count,
        chunks_used=[ChunkInfo(**c) for c in ctx.chunks_used],
        strategy_notes=ctx.strategy_notes,
        budget=TokenBudgetResponse(**budget_as_dict(ctx.budget)),
    )


def _get_or_build_rag(doc_id: str, raw_text: str) -> RAGPipeline:
    """Return cached RAG pipeline or build a new one."""
    if doc_id in _rag_cache:
        return _rag_cache[doc_id]

    # Try Redis cache
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url)
        cached = r.get(f"rag:{doc_id}")
        if cached:
            pipeline = RAGPipeline.deserialize(cached)
            _rag_cache[doc_id] = pipeline
            return pipeline
    except Exception:
        pass  # Redis unavailable, build fresh

    # Build fresh pipeline
    chunks = split_into_chunks(raw_text, target_tokens=settings.chunk_target_tokens,
                               overlap_tokens=settings.chunk_overlap_tokens)
    pipeline = RAGPipeline()
    pipeline.build_index(chunks)

    # Cache in Redis
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url)
        r.setex(f"rag:{doc_id}", settings.redis_cache_ttl, pipeline.serialize())
    except Exception:
        pass

    _rag_cache[doc_id] = pipeline
    return pipeline
