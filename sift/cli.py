"""Click CLI entrypoint for Sift."""

from __future__ import annotations

from pathlib import Path

import click

from sift import __version__
from sift.compare import build_comparison_table, load_report
from sift.extract import extract_chunks_from_file, is_test_chunk
from sift.ingest import ingest
from sift.output import scored_chunk_from_scores, write_outputs
from sift.scoring import ComplexityScorer, LintScorer, aggregate_scores


@click.group()
@click.version_option(__version__, prog_name="sift")
def main() -> None:
    """Sift — score Python functions and curate ranked fine-tuning datasets."""


@main.command("scan")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory for dataset.jsonl and report.json.",
)
@click.option(
    "--include-tests",
    is_flag=True,
    default=False,
    help="Include test chunks in scoring instead of excluding them by default.",
)
def scan(path: Path, output_dir: Path, include_tests: bool) -> None:
    """Scan PATH, score function chunks, and write ranked dataset outputs."""
    root, python_files = ingest(path)
    click.echo(f"Scanning {root} ({len(python_files)} Python file(s))...")

    scorers = [ComplexityScorer(), LintScorer()]
    lint_scorer = next(s for s in scorers if isinstance(s, LintScorer))
    scored = []
    excluded_test_chunks = 0

    for file_path in python_files:
        relative = str(file_path.relative_to(root))
        # Prime lint diagnostics against the real file (with full import/class
        # context) once per file, rather than re-running ruff per isolated
        # chunk — see LintScorer docstring for why this matters for accuracy.
        lint_scorer.prime_file(file_path, relative)
        for chunk in extract_chunks_from_file(file_path, relative_to=root):
            if not include_tests and is_test_chunk(chunk):
                excluded_test_chunks += 1
                continue
            scores = aggregate_scores(chunk, scorers)
            scored.append(scored_chunk_from_scores(chunk, scores))

    scored.sort(key=lambda item: item.final_score, reverse=True)
    dataset_path, report_path = write_outputs(
        scored,
        output_dir,
        test_chunks_excluded=excluded_test_chunks,
    )

    click.echo(f"Scored {len(scored)} chunk(s).")
    click.echo(f"Wrote {dataset_path}")
    click.echo(f"Wrote {report_path}")


@main.command("compare")
@click.argument("report_a", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path))
@click.argument("report_b", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path))
@click.option("--label-a", default=None, help="Label to use for the first report.")
@click.option("--label-b", default=None, help="Label to use for the second report.")
def compare(report_a: Path, report_b: Path, label_a: str | None, label_b: str | None) -> None:
    """Compare two report.json files side by side."""
    report_a_data = load_report(report_a)
    report_b_data = load_report(report_b)

    label_a_name = label_a or report_a.name
    label_b_name = label_b or report_b.name
    click.echo(build_comparison_table(report_a_data, report_b_data, label_a=label_a_name, label_b=label_b_name))


if __name__ == "__main__":
    main()
