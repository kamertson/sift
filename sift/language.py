"""Route file paths to the appropriate chunk extractor."""

from __future__ import annotations

from pathlib import Path

from sift.extract import Chunk, extract_chunks_from_file
from sift.extract_js import extract_js_chunks_from_file


def extract_chunks_for_file(path: Path, *, relative_to: Path | None = None) -> list[Chunk]:
    """Dispatch to the Python or JS/TS extractor based on file extension."""
    suffix = path.suffix.lower()
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return extract_js_chunks_from_file(path, relative_to=relative_to)
    return extract_chunks_from_file(path, relative_to=relative_to)
