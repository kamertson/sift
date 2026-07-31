from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_report(path: str | Path) -> dict[str, Any]:
    """Load a report JSON file from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_comparison_table(report_a: dict[str, Any], report_b: dict[str, Any], *, label_a: str, label_b: str) -> str:
    """Return a plain-text comparison table for two report payloads."""
    def fmt_value(value: Any) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    def distribution(report: dict[str, Any]) -> dict[str, Any]:
        dist = report.get("score_distribution") or {}
        return {
            "min": dist.get("min"),
            "max": dist.get("max"),
            "mean": dist.get("mean"),
            "median": dist.get("median"),
        }

    a_dist = distribution(report_a)
    b_dist = distribution(report_b)

    def delta(name: str) -> str:
        a_val = a_dist.get(name)
        b_val = b_dist.get(name)
        if a_val is None or b_val is None:
            return "N/A"
        return f"{b_val - a_val:+.3f}"

    lines = [
        f"{'metric':<25} {label_a:<20} {label_b:<20} {'delta (b-a)':<12}",
        f"{'-' * 25} {'-' * 20} {'-' * 20} {'-' * 12}",
        f"{'total_chunks':<25} {fmt_value(report_a.get('total_chunks')):<20} {fmt_value(report_b.get('total_chunks')):<20} {'':<12}",
        f"{'test_chunks_excluded':<25} {fmt_value(report_a.get('test_chunks_excluded')):<20} {fmt_value(report_b.get('test_chunks_excluded')):<20} {'':<12}",
        f"{'test_chunk_ratio':<25} {fmt_value(report_a.get('test_chunk_ratio')):<20} {fmt_value(report_b.get('test_chunk_ratio')):<20} {'':<12}",
        f"{'score_distribution.min':<25} {fmt_value(a_dist.get('min')):<20} {fmt_value(b_dist.get('min')):<20} {'':<12}",
        f"{'score_distribution.max':<25} {fmt_value(a_dist.get('max')):<20} {fmt_value(b_dist.get('max')):<20} {'':<12}",
        f"{'score_distribution.mean':<25} {fmt_value(a_dist.get('mean')):<20} {fmt_value(b_dist.get('mean')):<20} {delta('mean'):<12}",
        f"{'score_distribution.median':<25} {fmt_value(a_dist.get('median')):<20} {fmt_value(b_dist.get('median')):<20} {delta('median'):<12}",
    ]
    return "\n".join(lines)
