"""Click CLI entrypoint for Sift."""

from __future__ import annotations

from pathlib import Path

import click

from sift import __version__
from sift.extract import extract_chunks_from_file
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
def scan(path: Path, output_dir: Path) -> None:
    """Scan PATH, score function chunks, and write ranked dataset outputs."""
    root, python_files = ingest(path)
    click.echo(f"Scanning {root} ({len(python_files)} Python file(s))...")

    scorers = [ComplexityScorer(), LintScorer()]
    lint_scorer = next(s for s in scorers if isinstance(s, LintScorer))
    scored = []

    for file_path in python_files:
        relative = str(file_path.relative_to(root))
        # Prime lint diagnostics against the real file (with full import/class
        # context) once per file, rather than re-running ruff per isolated
        # chunk — see LintScorer docstring for why this matters for accuracy.
        lint_scorer.prime_file(file_path, relative)
        for chunk in extract_chunks_from_file(file_path, relative_to=root):
            scores = aggregate_scores(chunk, scorers)
            scored.append(scored_chunk_from_scores(chunk, scores))

    scored.sort(key=lambda item: item.final_score, reverse=True)
    dataset_path, report_path = write_outputs(scored, output_dir)

    click.echo(f"Scored {len(scored)} chunk(s).")
    click.echo(f"Wrote {dataset_path}")
    click.echo(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
