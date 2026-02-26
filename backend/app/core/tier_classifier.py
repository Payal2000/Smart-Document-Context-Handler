"""
Tier Classifier — assigns documents to T1–T4 based on token count.

Tier  Token Range      Strategy
----  ---------------  --------------------------
T1    ≤ 12,000         Direct injection (full doc)
T2    12,001–25,000    Smart trimming
T3    25,001–50,000    Strategic chunking + BM25 ranking
T4    > 50,000         RAG retrieval (FAISS + embeddings)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from loguru import logger


class Tier(IntEnum):
    T1 = 1
    T2 = 2
    T3 = 3
    T4 = 4


TIER_THRESHOLDS = {
    Tier.T1: 12_000,
    Tier.T2: 25_000,
    Tier.T3: 50_000,
    # T4: anything above 50K
}

TIER_LABELS = {
    Tier.T1: "Direct Injection",
    Tier.T2: "Smart Trimming",
    Tier.T3: "Strategic Chunking",
    Tier.T4: "RAG Retrieval",
}

TIER_COLORS = {
    Tier.T1: "#22c55e",   # green
    Tier.T2: "#3b82f6",   # blue
    Tier.T3: "#f59e0b",   # amber
    Tier.T4: "#ef4444",   # red
}


@dataclass
class TierResult:
    tier: Tier
    token_count: int
    label: str
    color: str
    description: str


def classify(token_count: int) -> TierResult:
    """Classify a document into a processing tier based on its token count."""
    if token_count <= TIER_THRESHOLDS[Tier.T1]:
        tier = Tier.T1
        description = "Full document fits in context window. No processing needed."
    elif token_count <= TIER_THRESHOLDS[Tier.T2]:
        tier = Tier.T2
        description = "Moderate size. Boilerplate removal and whitespace compression applied."
    elif token_count <= TIER_THRESHOLDS[Tier.T3]:
        tier = Tier.T3
        description = "Large document. Semantic chunking with BM25 relevance ranking."
    else:
        tier = Tier.T4
        description = "Very large document. Vector embeddings + FAISS retrieval."

    result = TierResult(
        tier=tier,
        token_count=token_count,
        label=TIER_LABELS[tier],
        color=TIER_COLORS[tier],
        description=description,
    )
    logger.info(f"Tier classification: {token_count:,} tokens → {tier.name} ({result.label})")
    return result
