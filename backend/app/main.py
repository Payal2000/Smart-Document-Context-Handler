"""
Smart Document Context Handler — FastAPI Application Entry Point
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import documents, query
from .config import get_settings
from .db.database import create_tables
from .utils.logging import setup_logging

settings = get_settings()
setup_logging(debug=settings.debug)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Intelligent 4-tier document context management system. "
        "Automatically selects the optimal strategy (direct injection, smart trimming, "
        "strategic chunking, or RAG retrieval) to fit documents into the LLM context window."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(documents.router, prefix="/api")
app.include_router(query.router, prefix="/api")


@app.on_event("startup")
async def on_startup() -> None:
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    await create_tables()


@app.get("/api/health", tags=["health"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
