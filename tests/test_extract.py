"""Tests for AST-based function/method chunk extraction."""

from __future__ import annotations

from pathlib import Path

from sift.extract import Chunk, extract_chunks, extract_chunks_from_file

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_repo"


def test_extract_chunks_shapes_and_count() -> None:
    """Extract chunks from the sample fixture and assert count/shape."""
    good = (FIXTURES / "good_code.py").read_text(encoding="utf-8")
    chunks = extract_chunks(good, "good_code.py")

    assert len(chunks) >= 2
    assert all(isinstance(c, Chunk) for c in chunks)

    for chunk in chunks:
        assert chunk.file == "good_code.py"
        assert isinstance(chunk.function_name, str) and chunk.function_name
        assert isinstance(chunk.code, str) and chunk.code.strip()
        assert chunk.start_line >= 1
        assert chunk.end_line >= chunk.start_line
        assert "def " in chunk.code or "async def " in chunk.code


def test_extract_includes_methods_and_docstrings() -> None:
    """Class methods should be qualified and retain docstrings when present."""
    mixed = (FIXTURES / "mixed.py").read_text(encoding="utf-8")
    chunks = extract_chunks(mixed, "mixed.py")
    names = {c.function_name for c in chunks}

    assert "Greeter.greet" in names
    greet = next(c for c in chunks if c.function_name == "Greeter.greet")
    assert greet.docstring is not None
    assert "greeting" in greet.docstring.lower()


def test_extract_chunks_from_sample_repo_files() -> None:
    """Reading fixture files from disk should yield a stable total chunk count."""
    all_chunks: list[Chunk] = []
    for path in sorted(FIXTURES.glob("*.py")):
        all_chunks.extend(extract_chunks_from_file(path, relative_to=FIXTURES))

    # good_code: 2 top-level funcs; messy_code: 2; mixed: 1 top-level + 2 methods
    assert len(all_chunks) == 7
    assert {c.file for c in all_chunks} == {"good_code.py", "messy_code.py", "mixed.py"}
