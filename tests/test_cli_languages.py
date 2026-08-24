"""CLI scan tests for multi-language extraction without JS/TS scoring."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sift.cli import main
from sift.extract import Chunk

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_repo_mixed"


def test_scan_default_python_only_leaves_js_unscored_field_at_zero(tmp_path: Path) -> None:
    """Default scan (no --languages) scores Python and reports 0 unscored language chunks."""
    repo = tmp_path / "mixed"
    shutil.copytree(FIXTURES, repo)
    out = tmp_path / "out"

    result = CliRunner().invoke(main, ["scan", str(repo), "-o", str(out)])

    assert result.exit_code == 0, result.output
    assert "Extracted but not yet scored" not in result.output

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["total_chunks"] == 2
    assert report["unscored_language_chunks"] == 0

    records = [
        json.loads(line)
        for line in (out / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(record["file"].endswith(".py") for record in records)
    assert {record["function_name"] for record in records} == {"add", "clamp"}


def test_scan_extracts_js_but_does_not_score_it(tmp_path: Path) -> None:
    """With --languages covering JS, extract JS chunks but never score them."""
    repo = tmp_path / "mixed"
    shutil.copytree(FIXTURES, repo)
    out = tmp_path / "out"

    scored_codes: list[str] = []
    primed_files: list[str] = []

    real_aggregate = __import__("sift.scoring", fromlist=["aggregate_scores"]).aggregate_scores

    def tracking_aggregate(chunk: Chunk, scorers, weights=None):
        scored_codes.append(chunk.code)
        assert chunk.file.endswith(".py"), f"scorer invoked on non-Python chunk: {chunk.file}"
        return real_aggregate(chunk, scorers, weights)

    with (
        patch("sift.cli.aggregate_scores", side_effect=tracking_aggregate) as mock_aggregate,
        patch("sift.cli.LintScorer.prime_file", autospec=True) as mock_prime,
    ):
        def tracking_prime(self, file_path: Path, relative_path: str) -> None:
            primed_files.append(relative_path)
            assert str(file_path).endswith(".py"), f"prime_file called on non-Python: {file_path}"

        mock_prime.side_effect = tracking_prime

        result = CliRunner().invoke(
            main,
            [
                "scan",
                str(repo),
                "-o",
                str(out),
                "--languages",
                "python,javascript",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Scored 2 chunk(s)." in result.output
    assert "Extracted but not yet scored: 2 JS/TS chunk(s) (no JS scorers yet)." in result.output

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["total_chunks"] == 2
    assert report["unscored_language_chunks"] == 2

    records = [
        json.loads(line)
        for line in (out / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 2
    assert all(record["file"].endswith(".py") for record in records)
    assert {record["function_name"] for record in records} == {"add", "clamp"}

    # Scorers must only have seen Python chunk source — never JS.
    assert mock_aggregate.call_count == 2
    assert all("function multiply" not in code and "const double" not in code for code in scored_codes)
    assert all("def add" in code or "def clamp" in code for code in scored_codes)
    assert primed_files == ["math_utils.py"]
