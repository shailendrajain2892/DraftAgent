"""Offline test for the comparative-retrieval metric math (no API)."""

from __future__ import annotations

from evals.compare_retrieval import _metrics


def test_metrics_perfect():
    m = _metrics([(["billing", "x", "y"], "billing"), (["intro", "a", "b"], "intro")])
    assert m == {"recall@1": 1.0, "recall@3": 1.0, "mrr": 1.0}


def test_metrics_rank_and_recall():
    # gold at rank 2 -> recall@1 miss, recall@3 hit, reciprocal 1/2
    m = _metrics([(["x", "billing", "y"], "billing")])
    assert m["recall@1"] == 0.0
    assert m["recall@3"] == 1.0
    assert m["mrr"] == 0.5


def test_metrics_miss():
    m = _metrics([(["x", "y", "z", "billing"], "billing")])
    assert m["recall@1"] == 0.0
    assert m["recall@3"] == 0.0  # gold only at rank 4
    assert m["mrr"] == 0.25
