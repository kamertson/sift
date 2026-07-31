from __future__ import annotations

from sift.compare import build_comparison_table


def test_build_comparison_table_handles_missing_fields() -> None:
    report_a = {"total_chunks": 10, "score_distribution": {"mean": 80.0, "median": 79.0}}
    report_b = {"total_chunks": 12, "test_chunks_excluded": 3, "test_chunk_ratio": 0.25}

    table = build_comparison_table(report_a, report_b, label_a="repo-a", label_b="repo-b")

    assert "repo-a" in table
    assert "repo-b" in table
    assert "test_chunks_excluded" in table
    assert "score_distribution.mean" in table
    assert "N/A" in table
    assert "0.250" in table
