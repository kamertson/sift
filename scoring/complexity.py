"""Complexity-based quality scorer using radon metrics."""

from __future__ import annotations

from radon.complexity import cc_visit
from radon.metrics import mi_visit

from sift.extract import Chunk
from sift.scoring.base import Scorer


class ComplexityScorer(Scorer):
    """Score chunks using cyclomatic complexity and maintainability index.

    Cyclomatic complexity is mapped so that simpler functions score higher.
    Radon's maintainability index already lives on a roughly ``0–100`` scale.
    The two signals are averaged to produce the final complexity score.
    """

    @property
    def name(self) -> str:
        return "complexity"

    def score(self, chunk: Chunk) -> float:
        """Compute a ``0–100`` complexity/maintainability score for *chunk*."""
        cc_score = self._cyclomatic_score(chunk.code)
        mi_score = self._maintainability_score(chunk.code)
        return _clamp(_average(cc_score, mi_score))

    def _cyclomatic_score(self, code: str) -> float:
        """Map cyclomatic complexity to ``0–100`` (lower complexity → higher)."""
        try:
            blocks = cc_visit(code)
        except SyntaxError:
            return 0.0

        if not blocks:
            return 100.0

        # Prefer the entry-point block complexity; fall back to the max.
        complexity = max(block.complexity for block in blocks)
        # Heuristic: CC 1 → 100, CC 10 → ~10, CC ≥ 11 → approaching 0.
        return _clamp(110.0 - (complexity * 10.0))

    def _maintainability_score(self, code: str) -> float:
        """Return radon's maintainability index clamped to ``0–100``."""
        try:
            # multi=True treats the snippet as a multi-block unit.
            mi = float(mi_visit(code, multi=True))
        except (SyntaxError, ZeroDivisionError, ValueError):
            return 0.0
        return _clamp(mi)


def _average(*values: float) -> float:
    return sum(values) / len(values)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))
