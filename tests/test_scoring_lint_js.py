"""Tests for JsLintScorer (ESLint-based JS/TS lint scoring)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sift.extract import Chunk
from sift.language import extract_chunks_for_file
from sift.scoring.lint_js import JsLintScorer, _ESLINT_BIN, _REPO_ROOT

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "lint_js"
MISSING_ESLINT = _REPO_ROOT / "node_modules" / ".bin" / "eslint-does-not-exist"


@pytest.fixture(scope="module")
def eslint_available() -> bool:
    """Skip integration tests when the pinned ESLint binary is not installed."""
    return _ESLINT_BIN.is_file()


@pytest.mark.skipif(not _ESLINT_BIN.is_file(), reason="ESLint not installed (run npm install)")
def test_prime_file_attributes_violations_to_chunk_line_ranges() -> None:
    """Violations in a chunk's line range reduce its score; clean chunks stay at 100."""
    path = FIXTURES / "violations.js"
    chunks = extract_chunks_for_file(path, relative_to=FIXTURES)
    by_name = {chunk.function_name: chunk for chunk in chunks}

    scorer = JsLintScorer()
    scorer.prime_file(path, "violations.js")

    clean_score = scorer.score(by_name["cleanAdd"])
    dirty_score = scorer.score(by_name["dirtyUnused"])

    assert clean_score == 100.0
    assert dirty_score < 100.0


@pytest.mark.skipif(not _ESLINT_BIN.is_file(), reason="ESLint not installed (run npm install)")
def test_prime_file_deducts_ten_points_per_violation() -> None:
    """Each violation in a chunk's line range costs 10 points off a 100 baseline."""
    path = FIXTURES / "violations.js"
    chunks = extract_chunks_for_file(path, relative_to=FIXTURES)
    dirty_chunk = next(chunk for chunk in chunks if chunk.function_name == "dirtyUnused")

    scorer = JsLintScorer()
    scorer.prime_file(path, "violations.js")

    assert scorer.score(dirty_chunk) == 90.0


@pytest.mark.skipif(not _ESLINT_BIN.is_file(), reason="ESLint not installed (run npm install)")
def test_isolated_fallback_scores_without_prime_file() -> None:
    """Isolated-snippet fallback works for unit tests without a prior prime_file()."""
    chunk = Chunk(
        code="function sample() {\n  const unused = 1;\n  return 0;\n}\n",
        file="sample.js",
        function_name="sample",
        start_line=1,
        end_line=3,
    )
    scorer = JsLintScorer()

    score = scorer.score(chunk)

    assert score < 100.0


def test_prime_file_raises_when_eslint_binary_missing(tmp_path: Path) -> None:
    """Missing node_modules/eslint must fail loudly, not silently return a score."""
    fake_file = tmp_path / "sample.js"
    fake_file.write_text("function noop() {}\n", encoding="utf-8")

    scorer = JsLintScorer()
    with patch("sift.scoring.lint_js._ESLINT_BIN", MISSING_ESLINT):
        with pytest.raises(RuntimeError, match="npm install"):
            scorer.prime_file(fake_file, "sample.js")


def test_isolated_fallback_raises_when_eslint_binary_missing() -> None:
    """Isolated fallback also requires the pinned ESLint binary."""
    chunk = Chunk(
        code="function noop() {}\n",
        file="noop.js",
        function_name="noop",
        start_line=1,
        end_line=1,
    )
    scorer = JsLintScorer()

    with patch("sift.scoring.lint_js._ESLINT_BIN", MISSING_ESLINT):
        with pytest.raises(RuntimeError, match="npm install"):
            scorer.score(chunk)


@pytest.mark.skipif(not _ESLINT_BIN.is_file(), reason="ESLint not installed (run npm install)")
def test_scorer_name_matches_python_lint_scorer() -> None:
    """JsLintScorer uses the same signal name for uniform report.json schema."""
    assert JsLintScorer().name == "lint"


@pytest.mark.skipif(not _ESLINT_BIN.is_file(), reason="ESLint not installed (run npm install)")
def test_prime_file_works_on_typescript_fixture() -> None:
    """TypeScript files lint via typescript-eslint without type-checked rules."""
    ts_fixture = FIXTURES / "clean.ts"
    chunks = extract_chunks_for_file(ts_fixture, relative_to=FIXTURES)
    clean_chunk = next(chunk for chunk in chunks if chunk.function_name == "cleanDouble")

    scorer = JsLintScorer()
    scorer.prime_file(ts_fixture, "clean.ts")

    assert scorer.score(clean_chunk) == 100.0
