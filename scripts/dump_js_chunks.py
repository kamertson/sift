"""Scratch script: walk a JS/TS repo, extract chunks, dump results to JSON.

Not part of the CLI — just for manually validating extract_js.py against a
real repository before building JS/TS scorers.

Usage:
    uv run python scripts/dump_js_chunks.py <repo_path> <output_json_path>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sift.ingest import ingest  # noqa: E402
from sift.language import extract_chunks_for_file  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: dump_js_chunks.py <repo_path> <output_json_path>")
        raise SystemExit(1)

    repo_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    root, files = ingest(repo_path, languages={"javascript", "typescript"})
    print(f"Found {len(files)} JS/TS file(s) under {root}")

    all_chunks = []
    parse_failures = []
    for file_path in files:
        relative = str(file_path.relative_to(root))
        chunks = extract_chunks_for_file(file_path, relative_to=root)
        if not chunks:
            # Could be a genuinely empty file, or a parse failure — flag it
            # so we can distinguish the two by eye.
            parse_failures.append(relative)
            continue
        for chunk in chunks:
            all_chunks.append(
                {
                    "file": chunk.file,
                    "function_name": chunk.function_name,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "line_count": chunk.end_line - chunk.start_line + 1,
                    "has_docstring": chunk.docstring is not None,
                    "code_preview": chunk.code[:200],
                }
            )

    summary = {
        "total_files_scanned": len(files),
        "total_chunks_extracted": len(all_chunks),
        "files_with_zero_chunks": len(parse_failures),
        "files_with_zero_chunks_sample": parse_failures[:20],
        "chunks": all_chunks,
    }

    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(all_chunks)} chunk(s) from {len(files)} file(s) to {output_path}")
    print(f"{len(parse_failures)} file(s) produced zero chunks (parse failure or genuinely empty)")


if __name__ == "__main__":
    main()
