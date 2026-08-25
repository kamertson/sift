"""Lint-based quality scorer using ESLint violation counts for JS/TS."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from sift.extract import Chunk
from sift.scoring.base import Scorer

# Each violation knocks this many points off a perfect 100 baseline.
_POINTS_PER_VIOLATION = 10.0
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ESLINT_BIN = _REPO_ROOT / "node_modules" / ".bin" / "eslint"


class JsLintScorer(Scorer):
    """Score JS/TS chunks by counting ESLint violations that fall within them.

    Violations are collected by running the repository-pinned ``eslint`` binary
    once per *whole file* via :meth:`prime_file`, then attributing each
    diagnostic's line number to whichever chunk's ``[start_line, end_line]``
    range contains it.

    This matters: running ESLint on an isolated function snippet (rather than
    the real file) strips away imports, module scope, and surrounding
    declarations. ESLint then reports spurious ``no-undef`` and similar
    violations for anything the snippet legitimately references from its
    original context — penalizing longer, more connected functions regardless
    of their actual quality, and rewarding trivial one-liners that have nothing
    left to flag. Scoring against the real file avoids this false-positive
    inflation.

    Callers MUST call :meth:`prime_file` for a chunk's file before calling
    :meth:`score` on chunks from that file; unprimed files fall back to the
    older isolated-snippet method, which is less accurate but keeps this
    scorer usable standalone (e.g. in unit tests scoring a bare chunk).

    The ESLint binary is resolved from ``node_modules/.bin/eslint`` at the
    Sift repository root (the pinned version from ``package.json``). If
    ``node_modules`` is missing, :meth:`prime_file` raises :class:`RuntimeError`
    rather than silently falling back to a global or auto-fetched ESLint.
    """

    def __init__(self, *, points_per_violation: float = _POINTS_PER_VIOLATION) -> None:
        self._points_per_violation = points_per_violation
        self._violation_lines_by_file: dict[str, list[int]] = {}

    @property
    def name(self) -> str:
        return "lint"

    def prime_file(self, file_path: Path, relative_path: str) -> None:
        """Run ESLint once against the real file and cache violation line numbers.

        Args:
            file_path: Absolute (or otherwise runnable) path to the real
                source file on disk — NOT a temp copy of an isolated chunk.
            relative_path: Key to cache under; should match ``Chunk.file`` for
                chunks extracted from this file so :meth:`score` can find it.

        Raises:
            RuntimeError: If the pinned local ESLint binary is not installed.
        """
        eslint = _require_eslint_bin()
        self._violation_lines_by_file[relative_path] = self._run_eslint_get_lines(
            eslint, file_path
        )

    def score(self, chunk: Chunk) -> float:
        """Return a ``0–100`` lint quality score for *chunk*."""
        cached_lines = self._violation_lines_by_file.get(chunk.file)
        if cached_lines is not None:
            violation_count = sum(
                1 for line in cached_lines if chunk.start_line <= line <= chunk.end_line
            )
        else:
            # Fallback for chunks scored without a prior prime_file() call.
            violation_count = self._count_violations_isolated(chunk)
        return max(0.0, 100.0 - (violation_count * self._points_per_violation))

    def _run_eslint_get_lines(self, eslint: Path, path: Path) -> list[int]:
        """Run ESLint on *path* and return the line number of each diagnostic."""
        result = subprocess.run(
            [
                str(eslint),
                "--format",
                "json",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        return self._parse_file_results(result.stdout)

    def _count_violations_isolated(self, chunk: Chunk) -> int:
        """Fallback: score a bare code snippet with no file context.

        Less accurate (prone to false-positive undefined-name violations)
        but keeps the scorer usable when no file has been primed.
        """
        eslint = _require_eslint_bin()
        suffix = Path(chunk.file).suffix.lower()
        if suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            suffix = ".js"

        with tempfile.TemporaryDirectory(prefix="sift-eslint-", dir=_REPO_ROOT) as tmp:
            path = Path(tmp) / f"chunk{suffix}"
            path.write_text(chunk.code, encoding="utf-8")
            result = subprocess.run(
                [
                    str(eslint),
                    "--format",
                    "json",
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT,
            )
        return len(self._parse_file_results(result.stdout))

    @staticmethod
    def _parse_file_results(stdout: str) -> list[int]:
        """Parse ESLint's JSON output into a flat list of violation line numbers."""
        if not stdout.strip():
            return []
        try:
            file_results = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        if not isinstance(file_results, list):
            return []

        lines: list[int] = []
        for file_result in file_results:
            if not isinstance(file_result, dict):
                continue
            messages = file_result.get("messages")
            if not isinstance(messages, list):
                continue
            for message in messages:
                if not isinstance(message, dict):
                    continue
                line = message.get("line")
                if isinstance(line, int):
                    lines.append(line)
        return lines


def _require_eslint_bin() -> Path:
    """Return the pinned ESLint binary path or raise with install instructions."""
    if not _ESLINT_BIN.is_file():
        raise RuntimeError(
            "ESLint is not installed. Run `npm install` in the Sift repository root "
            f"to install the pinned ESLint version expected at {_ESLINT_BIN}."
        )
    return _ESLINT_BIN
