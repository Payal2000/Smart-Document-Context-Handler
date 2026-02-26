"""
RAG Pipeline — FAISS vector store with OpenAI primary / sentence-transformers fallback.

Embedding strategy:
  - If OPENAI_API_KEY is set: use text-embedding-3-small (1536-dim)
  - Otherwise: use sentence-transformers all-MiniLM-L6-v2 (384-dim, local)

FAISS index is built per-document and optionally cached in Redis.
"""
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import Optional

import numpy as np
from loguru import logger

from .chunking_engine import Chunk


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float       # cosine similarity (0–1, higher is better)
    rank: int


class RAGPipeline:
    """
    Manages embeddings + FAISS index for a single document's chunks.
    """

    def __init__(self, use_openai: Optional[bool] = None):
        self._embedder = None
        self._use_openai = use_openai
        self._index = None          # faiss.IndexFlatIP
        self._chunks: list[Chunk] = []
        self._dim: Optional[int] = None

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder

        openai_key = os.getenv("OPENAI_API_KEY", "")
        use_openai = self._use_openai if self._use_openai is not None else bool(openai_key)

        if use_openai:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                self._embedder = ("openai", client)
                self._dim = 1536
                logger.info("Embedder: OpenAI text-embedding-3-small (1536-dim)")
                return self._embedder
            except Exception as e:
                logger.warning(f"OpenAI embedder failed ({e}), falling back to local")

        # Local fallback
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        self._embedder = ("local", model)
        self._dim = 384
        logger.info("Embedder: sentence-transformers all-MiniLM-L6-v2 (384-dim)")
        return self._embedder

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalized embedding matrix (n, dim)."""
        embedder_type, embedder = self._get_embedder()

        if embedder_type == "openai":
            response = embedder.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )
            vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
        else:
            vectors = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            vectors = np.array(vectors, dtype=np.float32)

        # L2-normalize for cosine similarity via dot product
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def build_index(self, chunks: list[Chunk]) -> None:
        """Embed all chunks and build a FAISS flat inner-product index."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu")

        if not chunks:
            raise ValueError("Cannot build index: no chunks provided")

        self._chunks = chunks
        texts = [c.text for c in chunks]

        logger.info(f"Embedding {len(texts)} chunks...")
        vectors = self._embed_texts(texts)
        self._dim = vectors.shape[1]

        self._index = faiss.IndexFlatIP(self._dim)   # inner product = cosine sim on normalized vecs
        self._index.add(vectors)
        logger.info(f"FAISS index built: {self._index.ntotal} vectors, dim={self._dim}")

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Retrieve the top-k most relevant chunks for a query."""
        if self._index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        import faiss

        query_vec = self._embed_texts([query])   # (1, dim)
        scores, indices = self._index.search(query_vec, min(top_k, len(self._chunks)))

        results = []
        for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), start=1):
            if idx == -1:
                continue
            results.append(RetrievedChunk(
                chunk=self._chunks[idx],
                score=float(score),
                rank=rank,
            ))

        logger.info(f"Retrieved {len(results)} chunks for query (top score: {results[0].score:.3f})" if results else "No results retrieved")
        return results

    # ------------------------------------------------------------------
    # Serialization (for Redis cache)
    # ------------------------------------------------------------------

    def serialize(self) -> bytes:
        """Serialize index + chunks to bytes for Redis storage."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu not installed.")

        index_bytes = faiss.serialize_index(self._index)
        payload = {
            "index_bytes": index_bytes.tobytes(),
            "chunks": self._chunks,
            "dim": self._dim,
            "use_openai": self._use_openai,
        }
        return pickle.dumps(payload)

    @classmethod
    def deserialize(cls, data: bytes) -> "RAGPipeline":
        """Restore a RAGPipeline from serialized bytes."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu not installed.")

        payload = pickle.loads(data)
        pipeline = cls(use_openai=payload["use_openai"])
        pipeline._chunks = payload["chunks"]
        pipeline._dim = payload["dim"]
        index_array = np.frombuffer(payload["index_bytes"], dtype=np.uint8)
        pipeline._index = faiss.deserialize_index(index_array)
        return pipeline


# ------------------------------------------------------------------
# BM25 ranking for Tier 3 (no embeddings needed)
# ------------------------------------------------------------------

def bm25_rank_chunks(chunks: list[Chunk], query: str, top_k: int) -> list[RetrievedChunk]:
    """
    Rank chunks using BM25 keyword scoring (fast, no embeddings).
    Used for Tier 3 where semantic search isn't required.
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        raise ImportError("rank-bm25 not installed. Run: pip install rank-bm25")

    tokenized_corpus = [c.text.lower().split() for c in chunks]
    tokenized_query = query.lower().split()

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    ranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        RetrievedChunk(chunk=chunk, score=float(score), rank=rank)
        for rank, (chunk, score) in enumerate(ranked[:top_k], start=1)
    ]
