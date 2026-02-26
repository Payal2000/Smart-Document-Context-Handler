"""Pydantic models for API request/response."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TokenBudgetResponse(BaseModel):
    total_window: int
    allocations: dict[str, int]
    document: dict[str, Any]


class TierInfo(BaseModel):
    tier: int
    label: str
    color: str
    description: str


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    file_size: int
    token_count: int
    tier: TierInfo
    budget: TokenBudgetResponse
    mime_type: Optional[str] = None
    page_count: Optional[int] = None
    row_count: Optional[int] = None
    created_at: datetime


class ChunkInfo(BaseModel):
    index: int
    tokens: int
    score: float


class QueryRequest(BaseModel):
    doc_id: str
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)


class QueryResponse(BaseModel):
    doc_id: str
    query: str
    tier: int
    assembled_context: str
    token_count: int
    chunks_used: list[ChunkInfo] = []
    strategy_notes: str
    budget: TokenBudgetResponse


class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_size: int
    token_count: int
    tier: int
    tier_label: str
    mime_type: Optional[str] = None
    page_count: Optional[int] = None
    row_count: Optional[int] = None
    created_at: datetime
