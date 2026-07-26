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

## Roadmap

**Multi-language support.** Sift is currently Python-only: the extraction layer
uses Python's built-in `ast` module, and the bundled scorers (`radon`, `ruff`)
are Python-specific tools. Both are language-bound by design choice, not by
architecture — the ingest/score/aggregate/output pipeline is already
language-agnostic.

The planned path to multi-language support:

1. **Swap the extraction layer to [`tree-sitter`](https://tree-sitter.github.io/tree-sitter/).**
   Tree-sitter has mature grammars for JS/TS, Go, Java, C, and most
   mainstream languages, and gives a single, consistent way to walk
   function/class-level chunks regardless of language. This solves chunk
   extraction once instead of writing a bespoke parser per language.
2. **Add per-language `Scorer` implementations** behind the existing
   `Scorer` interface. No changes needed to `aggregate.py` or `output.py`,
   since scoring and aggregation are already language-agnostic.
3. **Detect language per-file** during ingest and route each chunk to the
   right parser/scorer set, so a single `sift scan` can handle a
   polyglot repo in one pass.

### Language priority order

| Priority | Language | Complexity/lint tooling | Why this position |
| --- | --- | --- | --- |
| 1 | **JavaScript / TypeScript** | ESLint (violations, same shape as ruff) + `escomplex`/`typhonjs-escomplex` (complexity, same shape as radon) | Highest-value target: JS/TS is the most common language in code-LLM training corpora, so it's the strongest second data point for the "does quality filtering transfer across languages" claim. Tooling architecture closely mirrors the existing Python scorers, and tree-sitter's JS/TS grammar is the most mature available — lowest implementation risk for the highest payoff. |
| 2 | **Go** | `gocyclo` (complexity) + `golangci-lint` (violations) | Simple, well-behaved toolchain with no macro/preprocessor complications. Straightforward extension of the same `Scorer` pattern once JS/TS proves the multi-language architecture works end to end. |
| 3 | **Java** | Checkstyle / PMD (violations) + existing complexity tools | Widely used in enterprise codebases, which strengthens the B2B pitch, but more configuration overhead than Go (Checkstyle/PMD both need project-specific rule config to be meaningful). |
| 4 | **C** | `cppcheck` or `clang-tidy` (violations), complexity via `lizard` or similar | Deferred last: per-function chunk scoring is a weaker fit for what actually matters in C (memory safety, undefined behavior, pointer discipline) rather than complexity/lint alone, and the preprocessor (`#include`/`#define`) means tree-sitter parses unexpanded source, which can make chunk boundaries syntactically correct but semantically misleading (e.g. `#ifdef`-gated function variants). Needs its own dedicated signal set rather than reusing the ESLint-shaped pattern JS/TS, Go, and Java can share. |

This order is intentionally sequenced *after* the Python MVP is proven out
(real case-study repo, LLM-judge calibration, before/after fine-tune
result) — validating the core scoring approach on one language first is
lower-risk than generalizing early, and JS/TS is prioritized first within
that expansion because it offers the most leverage per unit of
implementation effort.
