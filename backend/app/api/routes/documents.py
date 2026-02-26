"""
Document upload and metadata endpoints.

POST /api/documents/upload  — upload and process a document
GET  /api/documents/{doc_id} — get document metadata
GET  /api/documents/         — list recent documents
"""
from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...config import get_settings
from ...core import (
    LoadedDocument,
    TierResult,
    allocate,
    budget_as_dict,
    classify,
    count_tokens,
    load_document,
)
from ...db.database import get_db
from ...db.models import Document, DocumentChunk
from ...models.document import DocumentMetadata, TierInfo, TokenBudgetResponse, UploadResponse

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Upload a document, analyze it, classify into a tier, and store metadata.
    Supported: .txt, .md, .pdf, .docx, .csv, .tsv, .xlsx
    """
    # Validate file size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
        )

    # Load and parse document
    try:
        loaded: LoadedDocument = load_document(file_bytes, file.filename or "upload")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Token counting and tier classification
    token_count = count_tokens(loaded.raw_text)
    tier_result: TierResult = classify(token_count)
    budget = allocate(token_count)

    # Save file to disk
    os.makedirs(settings.upload_dir, exist_ok=True)
    import uuid
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(settings.upload_dir, f"{doc_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Persist to database
    doc = Document(
        id=doc_id,
        filename=file.filename or "upload",
        file_size=file_size,
        token_count=token_count,
        tier=tier_result.tier.value,
        tier_label=tier_result.label,
        mime_type=loaded.mime_type,
        page_count=loaded.page_count,
        row_count=loaded.row_count,
        file_path=file_path,
    )
    db.add(doc)
    await db.flush()

    return UploadResponse(
        doc_id=doc_id,
        filename=loaded.filename,
        file_size=file_size,
        token_count=token_count,
        tier=TierInfo(
            tier=tier_result.tier.value,
            label=tier_result.label,
            color=tier_result.color,
            description=tier_result.description,
        ),
        budget=TokenBudgetResponse(**budget_as_dict(budget)),
        mime_type=loaded.mime_type,
        page_count=loaded.page_count,
        row_count=loaded.row_count,
        created_at=datetime.utcnow(),
    )


@router.get("/{doc_id}", response_model=DocumentMetadata)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentMetadata:
    """Get metadata for a previously uploaded document."""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    return DocumentMetadata(
        doc_id=doc.id,
        filename=doc.filename,
        file_size=doc.file_size,
        token_count=doc.token_count,
        tier=doc.tier,
        tier_label=doc.tier_label,
        mime_type=doc.mime_type,
        page_count=doc.page_count,
        row_count=doc.row_count,
        created_at=doc.created_at,
    )


@router.get("/", response_model=list[DocumentMetadata])
async def list_documents(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentMetadata]:
    """List the most recently uploaded documents."""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).limit(limit)
    )
    docs = result.scalars().all()
    return [
        DocumentMetadata(
            doc_id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            token_count=doc.token_count,
            tier=doc.tier,
            tier_label=doc.tier_label,
            mime_type=doc.mime_type,
            page_count=doc.page_count,
            row_count=doc.row_count,
            created_at=doc.created_at,
        )
        for doc in docs
    ]
