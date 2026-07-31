from __future__ import annotations

from sift.extract import Chunk
from sift.output import ScoredChunk, _reasons_for_low_score


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
