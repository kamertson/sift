"""Smoke-test JS/TS extraction against a real repository.

Usage:
    uv run python scripts/smoke_test_js_extraction.py <path-to-repo>

Walks the given directory for .js/.jsx/.ts/.tsx files, runs extract_js_chunks_from_file
on each, and reports:
  - total files scanned
  - files that produced zero chunks (potential parse failures or files with no
    top-level functions/classes worth investigating)
  - total chunks extracted
  - a few sample chunks for manual eyeballing
"""

from __future__ import annotations

import sys
from pathlib import Path

from sift.extract_js import extract_js_chunks_from_file

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "coverage", ".next", "test", "tests",
}
SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/smoke_test_js_extraction.py <path-to-repo>")
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    files = [
        p
        for p in root.rglob("*")
        if p.suffix in SUFFIXES
        and p.is_file()
        and not any(part in SKIP_DIRS for part in p.parts)
    ]

    total_chunks = 0
    zero_chunk_files: list[Path] = []
    samples: list[str] = []

    for path in sorted(files):
        chunks = extract_js_chunks_from_file(path, relative_to=root)
        total_chunks += len(chunks)
        if not chunks:
            zero_chunk_files.append(path.relative_to(root))
        elif len(samples) < 10:
            for chunk in chunks[:2]:
                samples.append(f"  {chunk.file}:{chunk.start_line}-{chunk.end_line}  {chunk.function_name}")

    print(f"Scanned {len(files)} JS/TS file(s) under {root}")
    print(f"Total chunks extracted: {total_chunks}")
    print(f"Files with zero chunks: {len(zero_chunk_files)} / {len(files)}")
    print()
    print("Sample extracted chunks:")
    for line in samples:
        print(line)
    print()
    print("Files with zero chunks (first 20, worth spot-checking a few by hand):")
    for path in zero_chunk_files[:20]:
        print(f"  {path}")


if __name__ == "__main__":
    main()
