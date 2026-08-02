"""Bisect script: find which file segfaults extract_js_chunks_from_file.

Prints each file before processing it, so if the process crashes, the last
printed filename is the culprit (stdout is unbuffered via -u).

Usage:
    uv run python -u scripts/bisect_js_crash.py <repo_path>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sift.ingest import ingest  # noqa: E402
from sift.language import extract_chunks_for_file  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: bisect_js_crash.py <repo_path>")
        raise SystemExit(1)

    repo_path = Path(sys.argv[1])
    root, files = ingest(repo_path, languages={"javascript", "typescript"})
    print(f"Found {len(files)} JS/TS file(s) under {root}", flush=True)

    for i, file_path in enumerate(files):
        relative = str(file_path.relative_to(root))
        print(f"[{i + 1}/{len(files)}] {relative}", flush=True)
        extract_chunks_for_file(file_path, relative_to=root)

    print("Done — no crash.", flush=True)


if __name__ == "__main__":
    main()
