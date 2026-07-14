"""Combine multiple scorer signals into a single quality score."""

from __future__ import annotations

from typing import Mapping

from sift.extract import Chunk
from sift.scoring.base import Scorer


def aggregate_scores(
    chunk: Chunk,
    scorers: list[Scorer],
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Run *scorers* on *chunk* and return per-signal plus final scores.

    Each scorer's output is assumed to already be on a ``0–100`` scale. When
    *weights* is omitted, signals are combined with **equal weights**.

    TODO: Calibrate these weights later against an LLM-judge sample so the
    composite ranking better matches human/model quality preferences.

    Args:
        chunk: Code chunk to score.
        scorers: Pluggable scorer instances (order does not matter).
        weights: Optional mapping of ``scorer.name → weight``. Missing names
            default to ``1.0``. Weights are normalized to sum to ``1``.

    Returns:
        Dict with one ``\"{name}_score\"`` entry per scorer plus ``\"final_score\"``.
    """
    if not scorers:
        raise ValueError("aggregate_scores requires at least one Scorer")

    raw: dict[str, float] = {}
    for scorer in scorers:
        raw[scorer.name] = float(scorer.score(chunk))

    effective_weights = {
        name: float(weights.get(name, 1.0) if weights is not None else 1.0) for name in raw
    }
    weight_sum = sum(effective_weights.values())
    if weight_sum <= 0:
        raise ValueError("scorer weights must sum to a positive value")

    final = sum(raw[name] * (effective_weights[name] / weight_sum) for name in raw)

    result = {f"{name}_score": score for name, score in raw.items()}
    result["final_score"] = final
    return result
