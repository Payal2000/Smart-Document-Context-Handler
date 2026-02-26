"""Tests for token budget allocation."""
import pytest
from app.core.budget_allocator import (
    DOCUMENT_MAX,
    HISTORY_BUDGET,
    RESPONSE_BUFFER,
    SYSTEM_PROMPT_BUDGET,
    TOTAL_WINDOW,
    allocate,
    budget_as_dict,
)


def test_total_adds_up():
    assert (
        SYSTEM_PROMPT_BUDGET + HISTORY_BUDGET + RESPONSE_BUFFER + DOCUMENT_MAX == TOTAL_WINDOW
    )


def test_small_doc_gets_full_allocation():
    budget = allocate(5000)
    assert budget.document_allocated == 5000


def test_large_doc_capped_at_max():
    budget = allocate(300_000)
    assert budget.document_allocated == DOCUMENT_MAX
    assert budget.doc_tokens_original == 300_000


def test_utilization_pct():
    budget = allocate(TOTAL_WINDOW // 2)
    assert 0 < budget.utilization_pct <= 100


def test_budget_as_dict_structure():
    budget = allocate(10_000)
    d = budget_as_dict(budget)
    assert "total_window" in d
    assert "allocations" in d
    assert "document" in d
    assert d["allocations"]["system_prompt"] == SYSTEM_PROMPT_BUDGET
    assert d["document"]["truncated"] is False


def test_truncation_flag():
    budget = allocate(DOCUMENT_MAX + 1)
    d = budget_as_dict(budget)
    assert d["document"]["truncated"] is True
