"""Serialize scored chunks to dataset.jsonl and a summary report.json."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from sift.extract import Chunk


@dataclass(frozen=True)
class ScoredChunk:
    """A chunk paired with its quality scores."""

    chunk: Chunk
    complexity_score: float
    lint_score: float
    final_score: float
    scores: dict[str, float]

    def to_record(self) -> dict[str, Any]:
        """Return the flat JSONL record schema for this scored chunk."""
        return {
            "code": self.chunk.code,
            "file": self.chunk.file,
            "function_name": self.chunk.function_name,
            "start_line": self.chunk.start_line,
            "end_line": self.chunk.end_line,
            "complexity_score": self.complexity_score,
            "lint_score": self.lint_score,
            "final_score": self.final_score,
        }


def write_outputs(
    scored: Sequence[ScoredChunk],
    output_dir: str | Path,
    *,
    test_chunks_excluded: int = 0,
) -> tuple[Path, Path]:
    """Write ``dataset.jsonl`` and ``report.json`` under *output_dir*.

    Chunks are written in the order provided; callers should sort descending
    by ``final_score`` before invoking this helper.

    Args:
        scored: Ranked scored chunks.
        output_dir: Directory to create/write into.

    Returns:
        Paths to the written ``dataset.jsonl`` and ``report.json`` files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    dataset_path = out / "dataset.jsonl"
    report_path = out / "report.json"

    with dataset_path.open("w", encoding="utf-8") as handle:
        for item in scored:
            handle.write(json.dumps(item.to_record(), ensure_ascii=False) + "\n")

    report = build_report(scored, test_chunks_excluded=test_chunks_excluded)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dataset_path, report_path


def build_report(
    scored: Sequence[ScoredChunk],
    *,
    test_chunks_excluded: int = 0,
) -> dict[str, Any]:
    """Build summary statistics and top/bottom exemplars for *scored*."""
    total_extracted = len(scored) + test_chunks_excluded
    if not scored:
        return {
            "total_chunks": 0,
            "test_chunks_excluded": test_chunks_excluded,
            "test_chunk_ratio": _round_ratio(test_chunks_excluded, total_extracted),
            "score_distribution": {"min": None, "max": None, "mean": None, "median": None},
            "top_5_highest": [],
            "top_5_lowest": [],
        }

    finals = [item.final_score for item in scored]
    ranked_high = sorted(scored, key=lambda s: s.final_score, reverse=True)
    ranked_low = sorted(scored, key=lambda s: s.final_score)

    # With small chunk counts, "top 5 highest" and "top 5 lowest" can overlap
    # (e.g. 7 total chunks can't have 5 distinct highest AND 5 distinct lowest).
    # Cap each side so they never share entries, and flag when this happened.
    n = len(scored)
    k = min(5, n // 2) if n < 10 else 5
    small_sample = n < 10

    return {
        "total_chunks": n,
        "test_chunks_excluded": test_chunks_excluded,
        "test_chunk_ratio": _round_ratio(test_chunks_excluded, total_extracted),
        "small_sample_warning": (
            "Fewer than 10 chunks scored; top/bottom exemplars are limited to "
            f"{k} each to avoid overlap and may not be statistically meaningful."
            if small_sample
            else None
        ),
        "score_distribution": {
            "min": min(finals),
            "max": max(finals),
            "mean": statistics.fmean(finals),
            "median": statistics.median(finals),
        },
        "top_5_highest": [_exemplar(item) for item in ranked_high[:k]],
        "top_5_lowest": [
            _exemplar(item, include_reasons=True, small_sample=small_sample)
            for item in ranked_low[:k]
        ],
    }


def _exemplar(
    item: ScoredChunk,
    *,
    include_reasons: bool = False,
    small_sample: bool = False,
) -> dict[str, Any]:
    """Compact summary of a scored chunk for the report."""
    payload: dict[str, Any] = {
        "file": item.chunk.file,
        "function_name": item.chunk.function_name,
        "start_line": item.chunk.start_line,
        "end_line": item.chunk.end_line,
        "complexity_score": item.complexity_score,
        "lint_score": item.lint_score,
        "final_score": item.final_score,
    }
    if include_reasons:
        payload["reasons"] = _reasons_for_low_score(item, small_sample=small_sample)
    return payload


def _reasons_for_low_score(item: ScoredChunk, *, small_sample: bool = False) -> list[str]:
    """Human-readable hints explaining why a chunk scored poorly.

    Note: with a small total chunk count, a chunk can land in the "lowest"
    bucket purely because there aren't enough chunks to fill 5 distinct
    highest/lowest slots, not because it actually scored poorly in absolute
    terms. In that case we say so explicitly instead of implying a quality
    problem that isn't there.
    """
    reasons: list[str] = []
    if item.complexity_score < 50:
        reasons.append(
            f"Low complexity/maintainability score ({item.complexity_score:.1f}/100)"
        )
    if item.lint_score < 50:
        reasons.append(f"High lint violation pressure ({item.lint_score:.1f}/100)")
    if not reasons and item.final_score >= 70:
        if small_sample:
            reasons.append(
                f"No quality issues detected (final score {item.final_score:.1f}/100); "
                "appears here only due to small sample size"
            )
        else:
            reasons.append(
                f"No significant quality issues detected (final score {item.final_score:.1f}/100); "
                "ranks lowest only relative to other chunks in this dataset."
            )
    elif not reasons:
        reasons.append("Below peer average on combined quality signals")
    return reasons


def _round_ratio(numerator: int, denominator: int) -> float | None:
    """Return a rounded ratio or ``None`` when the denominator is zero."""
    if denominator == 0:
        return None
    return round(numerator / denominator, 3)


def scored_chunk_from_scores(chunk: Chunk, scores: dict[str, float]) -> ScoredChunk:
    """Wrap a chunk and aggregate score dict into a :class:`ScoredChunk`."""
    return ScoredChunk(
        chunk=chunk,
        complexity_score=float(scores.get("complexity_score", 0.0)),
        lint_score=float(scores.get("lint_score", 0.0)),
        final_score=float(scores["final_score"]),
        scores=dict(scores),
    )


__all__ = [
    "ScoredChunk",
    "build_report",
    "scored_chunk_from_scores",
    "write_outputs",
]
