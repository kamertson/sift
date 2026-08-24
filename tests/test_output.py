"""Tests for report fields related to excluded / unscored chunks."""

from __future__ import annotations

from sift.extract import Chunk
from sift.output import ScoredChunk, _reasons_for_low_score, build_report


def _make_scored_chunk(final_score: float = 85.0) -> ScoredChunk:
    chunk = Chunk(
        code="def sample():\n    return 1\n",
        file="sample.py",
        function_name="sample",
        start_line=1,
        end_line=2,
    )
    return ScoredChunk(
        chunk=chunk,
        complexity_score=80.0,
        lint_score=80.0,
        final_score=final_score,
        scores={
            "complexity_score": 80.0,
            "lint_score": 80.0,
            "final_score": final_score,
        },
    )


def test_reasons_for_low_score_small_sample_message() -> None:
    item = _make_scored_chunk(final_score=75.0)

    reasons = _reasons_for_low_score(item, small_sample=True)

    assert reasons == [
        "No quality issues detected (final score 75.0/100); appears here only due to small sample size"
    ]


def test_reasons_for_low_score_large_sample_message() -> None:
    item = _make_scored_chunk(final_score=75.0)

    reasons = _reasons_for_low_score(item, small_sample=False)

    assert reasons == [
        "No significant quality issues detected (final score 75.0/100); ranks lowest only relative to other chunks in this dataset."
    ]


def test_build_report_includes_unscored_language_chunks_default_zero() -> None:
    report = build_report([_make_scored_chunk()])

    assert report["unscored_language_chunks"] == 0
    assert report["test_chunks_excluded"] == 0


def test_build_report_tracks_unscored_language_chunks() -> None:
    report = build_report(
        [_make_scored_chunk(), _make_scored_chunk(final_score=70.0)],
        test_chunks_excluded=1,
        unscored_language_chunks=3,
    )

    assert report["total_chunks"] == 2
    assert report["test_chunks_excluded"] == 1
    assert report["unscored_language_chunks"] == 3
    # 2 scored + 1 test + 3 unscored language = 6 extracted
    assert report["test_chunk_ratio"] == round(1 / 6, 3)
