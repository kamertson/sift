"""Lint-based quality scorer using ruff violation counts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sift.extract import Chunk
from sift.scoring.base import Scorer

# Each violation knocks this many points off a perfect 100 baseline.
_POINTS_PER_VIOLATION = 10.0


class LintScorer(Scorer):
    """Score chunks by counting ruff lint violations that fall within them.

    Violations are collected by running ``ruff check`` once per *whole file*
    via :meth:`prime_file`, then attributing each diagnostic's line number to
    whichever chunk's ``[start_line, end_line]`` range contains it.

    This matters: running ruff on an isolated, dedented function snippet
    (rather than the real file) strips away imports, class context, and
    surrounding names. Ruff then reports spurious "undefined name" and
    similar violations for anything the snippet legitimately references from
    its original context — penalizing longer, more connected functions
    regardless of their actual quality, and rewarding trivial one-liners
    that have nothing left to flag. Scoring against the real file avoids
    this false-positive inflation.

    Callers MUST call :meth:`prime_file` for a chunk's file before calling
    :meth:`score` on that chunk's file; unprimed files fall back to the
    older isolated-snippet method, which is less accurate but keeps this
    scorer usable standalone (e.g. in unit tests scoring a bare chunk).
    """

    def __init__(self, *, points_per_violation: float = _POINTS_PER_VIOLATION) -> None:
        self._points_per_violation = points_per_violation
        self._violation_lines_by_file: dict[str, list[int]] = {}

    @property
    def name(self) -> str:
        return "lint"

    def prime_file(self, file_path: Path, relative_path: str) -> None:
        """Run ruff once against the real file and cache violation line numbers.

        Args:
            file_path: Absolute (or otherwise runnable) path to the real
                source file on disk — NOT a temp copy of an isolated chunk.
            relative_path: Key to cache under; should match ``Chunk.file`` for
                chunks extracted from this file so :meth:`score` can find it.
        """
        self._violation_lines_by_file[relative_path] = self._run_ruff_get_lines(file_path)

    def score(self, chunk: Chunk) -> float:
        """Return a ``0–100`` lint quality score for *chunk*."""
        cached_lines = self._violation_lines_by_file.get(chunk.file)
        if cached_lines is not None:
            violation_count = sum(
                1 for line in cached_lines if chunk.start_line <= line <= chunk.end_line
            )
        else:
            # Fallback for chunks scored without a prior prime_file() call.
            violation_count = self._count_violations_isolated(chunk.code)
        return max(0.0, 100.0 - (violation_count * self._points_per_violation))

    def _run_ruff_get_lines(self, path: Path) -> list[int]:
        """Run ruff on *path* and return the line number of each diagnostic."""
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
        diagnostics = self._parse_diagnostics(result.stdout)
        lines: list[int] = []
        for diag in diagnostics:
            location = diag.get("location") or {}
            row = location.get("row")
            if isinstance(row, int):
                lines.append(row)
        return lines

    def _count_violations_isolated(self, code: str) -> int:
        """Fallback: score a bare code snippet with no file context.

        Less accurate (prone to false-positive undefined-name violations)
        but keeps the scorer usable when no file has been primed.
        """
        import tempfile

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
        return len(self._parse_diagnostics(result.stdout))

    @staticmethod
    def _parse_diagnostics(stdout: str) -> list[dict]:
        """Parse ruff's JSON diagnostics output, tolerating empty/bad output."""
        if not stdout.strip():
            return []
        try:
            diagnostics = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        return diagnostics if isinstance(diagnostics, list) else []
