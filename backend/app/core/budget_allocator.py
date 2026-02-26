"""
Token Budget Allocator — splits the 200K context window into named allocations.

Total window: 200,000 tokens
  System prompt:        2,000  (fixed)
  Conversation history: 10,000 (fixed)
  Response buffer:       4,000  (fixed)
  Document content:   184,000  (max; actual = min(doc_tokens, 184,000))
"""
from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

TOTAL_WINDOW = 200_000
SYSTEM_PROMPT_BUDGET = 2_000
HISTORY_BUDGET = 10_000
RESPONSE_BUFFER = 4_000
DOCUMENT_MAX = TOTAL_WINDOW - SYSTEM_PROMPT_BUDGET - HISTORY_BUDGET - RESPONSE_BUFFER  # 184,000


@dataclass
class TokenBudget:
    total_window: int
    system_prompt: int
    conversation_history: int
    response_buffer: int
    document_allocated: int   # how many tokens we're actually using for the doc
    document_max: int         # upper limit
    doc_tokens_original: int  # token count before any processing
    utilization_pct: float    # document_allocated / total_window * 100


def allocate(doc_token_count: int) -> TokenBudget:
    """
    Given the token count of a (possibly pre-processed) document,
    compute how many tokens to allocate to it and return a full budget.
    """
    document_allocated = min(doc_token_count, DOCUMENT_MAX)
    utilization = (document_allocated / TOTAL_WINDOW) * 100

    budget = TokenBudget(
        total_window=TOTAL_WINDOW,
        system_prompt=SYSTEM_PROMPT_BUDGET,
        conversation_history=HISTORY_BUDGET,
        response_buffer=RESPONSE_BUFFER,
        document_allocated=document_allocated,
        document_max=DOCUMENT_MAX,
        doc_tokens_original=doc_token_count,
        utilization_pct=round(utilization, 2),
    )

    logger.info(
        f"Budget: doc={document_allocated:,}/{DOCUMENT_MAX:,} tokens "
        f"({budget.utilization_pct}% of total window)"
    )
    return budget


def budget_as_dict(budget: TokenBudget) -> dict:
    """Serializable dict for the API response."""
    return {
        "total_window": budget.total_window,
        "allocations": {
            "system_prompt": budget.system_prompt,
            "conversation_history": budget.conversation_history,
            "response_buffer": budget.response_buffer,
            "document_content": budget.document_allocated,
        },
        "document": {
            "original_tokens": budget.doc_tokens_original,
            "allocated_tokens": budget.document_allocated,
            "max_tokens": budget.document_max,
            "utilization_pct": budget.utilization_pct,
            "truncated": budget.doc_tokens_original > budget.document_max,
        },
    }
