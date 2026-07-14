"""Lint-based quality scorer using ruff violation counts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from sift.extract import Chunk
from sift.scoring.base import Scorer

# Each violation knocks this many points off a perfect 100 baseline.
_POINTS_PER_VIOLATION = 10.0


class LintScorer(Scorer):
    """Score chunks by counting ruff lint violations overlapping the chunk.

    Violations are collected by running ``python -m ruff check`` on a temporary
    file containing the chunk source (so line numbers align with the snippet).
    Fewer violations produce higher scores, normalized to ``0–100``.
    """

    def __init__(self, *, points_per_violation: float = _POINTS_PER_VIOLATION) -> None:
        self._points_per_violation = points_per_violation

    @property
    def name(self) -> str:
        return "lint"

    def score(self, chunk: Chunk) -> float:
        """Return a ``0–100`` lint quality score for *chunk*."""
        violation_count = self._count_violations(chunk.code)
        return max(0.0, 100.0 - (violation_count * self._points_per_violation))

    def _count_violations(self, code: str) -> int:
        """Run ruff on *code* and return the number of reported diagnostics."""
        with tempfile.TemporaryDirectory(prefix="sift-ruff-") as tmp:
            path = Path(tmp) / "chunk.py"
            path.write_text(code, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--output-format",
                    "json",
                    "--exit-zero",
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        if not result.stdout.strip():
            return 0

        try:
            diagnostics = json.loads(result.stdout)
        except json.JSONDecodeError:
            return 0

        if not isinstance(diagnostics, list):
            return 0
        return len(diagnostics)
