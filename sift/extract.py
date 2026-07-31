"""Extract function- and method-level code chunks from Python source files."""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass
from pathlib import Path, PurePath


@dataclass(frozen=True)
class Chunk:
    """A single function or method extracted from a Python file.

    Attributes:
        code: Exact source text of the function or method.
        file: Path to the source file, relative to the scan root when available.
        function_name: Qualified name (e.g. ``MyClass.method`` or ``helper``).
        start_line: 1-based inclusive start line in the source file.
        end_line: 1-based inclusive end line in the source file.
        docstring: Function docstring if present, otherwise ``None``.
    """

    code: str
    file: str
    function_name: str
    start_line: int
    end_line: int
    docstring: str | None = None


def is_test_chunk(chunk: Chunk) -> bool:
    """Return True when a chunk appears to be test code."""
    path = PurePath(chunk.file)
    basename = path.name
    parts = {part for part in path.parts if part not in {".", ""}}

    if any(part in {"test", "tests"} for part in parts):
        return True
    if basename.startswith("test_") or basename.endswith("_test.py"):
        return True

    function_name = chunk.function_name
    if function_name.startswith("test_"):
        return True
    if "." in function_name:
        class_name = function_name.split(".", 1)[0]
        if class_name.startswith("Test"):
            return True

    return False


def extract_chunks(source: str, file_path: str | Path) -> list[Chunk]:
    """Parse *source* and return one :class:`Chunk` per top-level function/method.

    Top-level functions and methods nested directly under classes are extracted.
    Nested functions defined inside other functions are ignored for the MVP.

    Args:
        source: Full Python source text of the file.
        file_path: Path used for chunk metadata (stored as a string).

    Returns:
        List of extracted chunks in source order.

    Raises:
        SyntaxError: If *source* cannot be parsed as Python.
    """
    tree = ast.parse(source)
    path_str = str(file_path)
    lines = source.splitlines(keepends=True)
    chunks: list[Chunk] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(_chunk_from_function(node, lines, path_str, qualifier=None))
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunks.append(
                        _chunk_from_function(child, lines, path_str, qualifier=node.name)
                    )

    return chunks


def extract_chunks_from_file(path: Path, *, relative_to: Path | None = None) -> list[Chunk]:
    """Read a Python file from disk and extract chunks.

    Args:
        path: Absolute or relative path to a ``.py`` file.
        relative_to: If provided, store the file path relative to this root.

    Returns:
        Extracted chunks for the file. Returns an empty list on syntax errors
        so a full-repo scan can continue past unparsable files.
    """
    source = path.read_text(encoding="utf-8", errors="replace")
    display = str(path.relative_to(relative_to)) if relative_to is not None else str(path)
    try:
        return extract_chunks(source, display)
    except SyntaxError:
        return []


def _chunk_from_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    lines: list[str],
    file_path: str,
    qualifier: str | None,
) -> Chunk:
    """Build a :class:`Chunk` from an AST function/method node."""
    start = node.lineno
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    # Include decorators in the captured span when present.
    if node.decorator_list:
        start = min(d.lineno for d in node.decorator_list)

    # Dedent so methods remain valid standalone Python for scorers (radon/ruff).
    code = textwrap.dedent("".join(lines[start - 1 : end]))
    name = f"{qualifier}.{node.name}" if qualifier else node.name
    docstring = ast.get_docstring(node)

    return Chunk(
        code=code,
        file=file_path,
        function_name=name,
        start_line=start,
        end_line=end,
        docstring=docstring,
    )
