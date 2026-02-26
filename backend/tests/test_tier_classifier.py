"""Tests for tier classification logic."""
import pytest
from app.core.tier_classifier import Tier, classify


def test_t1_boundary():
    result = classify(12_000)
    assert result.tier == Tier.T1


def test_t1_small():
    result = classify(100)
    assert result.tier == Tier.T1


def test_t2_lower():
    result = classify(12_001)
    assert result.tier == Tier.T2


def test_t2_upper():
    result = classify(25_000)
    assert result.tier == Tier.T2


def test_t3_lower():
    result = classify(25_001)
    assert result.tier == Tier.T3


def test_t3_upper():
    result = classify(50_000)
    assert result.tier == Tier.T3


def test_t4():
    result = classify(50_001)
    assert result.tier == Tier.T4


def test_t4_large():
    result = classify(500_000)
    assert result.tier == Tier.T4


def test_result_has_color():
    result = classify(5_000)
    assert result.color.startswith("#")


def test_result_has_label():
    result = classify(5_000)
    assert "Direct Injection" in result.label
