# Sift

CLI tool that scans a Python codebase, scores each function for code quality, and outputs a curated, ranked dataset intended for ML fine-tuning data curation.

## Install

Requires Python 3.11+. Using [`uv`](https://github.com/astral-sh/uv) (recommended):

```bash
uv sync --extra dev
```

Or with pip:

```bash
pip install -e ".[dev]"
```

## Usage

Scan a local repository (or any directory of Python files):

```bash
sift scan ./path/to/repo
```

Options:

```bash
sift scan ./path/to/repo --output-dir ./out
sift scan ./path/to/repo -o ./out
```

### Example

```bash
# From the repo root after install
sift scan ./fixtures/sample_repo -o ./out
```

This writes:

- `dataset.jsonl` — one scored function/method chunk per line
- `report.json` — summary stats plus top/bottom examples

### Output schema

Each JSONL record looks like:

```json
{
  "code": "def add(a, b):\n    return a + b\n",
  "file": "math_utils.py",
  "function_name": "add",
  "start_line": 1,
  "end_line": 2,
  "complexity_score": 95.0,
  "lint_score": 100.0,
  "final_score": 97.5
}
```

Scores are normalized to **0–100** (higher is better). The MVP averages complexity and lint signals with equal weight; weights should be calibrated later against an LLM-judge sample.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run sift scan ./fixtures/sample_repo -o ./out
```

## Architecture

| Module | Role |
| --- | --- |
| `sift.ingest` | Walk a tree (or git repo), find `.py` files, respect `.gitignore` |
| `sift.extract` | Parse with `ast`, emit function/method chunks |
| `sift.scoring.*` | Pluggable scorers + weighted aggregation |
| `sift.output` | Write `dataset.jsonl` and `report.json` |
| `sift.cli` | Click entrypoint: `sift scan <path>` |
