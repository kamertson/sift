"""Extract JavaScript and TypeScript chunks with tree-sitter."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_javascript
import tree_sitter_typescript

from sift.extract import Chunk

_JS_LANGUAGE = Language(tree_sitter_javascript.language())
_TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
_TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
_WHITESPACE = b" \t\r\n"


def extract_js_chunks(source: str, file_path: str) -> list[Chunk]:
    """Parse JS/TS source and return extracted chunks in source order."""
    parser = _parser_for_path(file_path)
    if parser is None:
        return []

    try:
        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
    except Exception:
        return []

    if tree.root_node.has_error:
        return []

    chunks: list[Chunk] = []
    for node in tree.root_node.named_children:
        chunks.extend(_extract_from_node(node, source_bytes, file_path))

    chunks.sort(key=lambda item: (item.start_line, item.end_line, item.function_name))
    return chunks


def extract_js_chunks_from_file(path: Path, *, relative_to: Path | None = None) -> list[Chunk]:
    """Read a JS/TS file from disk and extract chunks."""
    source = path.read_text(encoding="utf-8", errors="replace")
    display = str(path.relative_to(relative_to)) if relative_to is not None else str(path)
    try:
        return extract_js_chunks(source, display)
    except Exception:
        return []


def _parser_for_path(file_path: str) -> Parser | None:
    suffix = Path(file_path).suffix.lower()
    if suffix in {".js", ".jsx"}:
        language = _JS_LANGUAGE
    elif suffix == ".ts":
        language = _TS_LANGUAGE
    elif suffix == ".tsx":
        language = _TSX_LANGUAGE
    else:
        return None

    parser = Parser()
    parser.language = language
    return parser


def _extract_from_node(
    node,
    source_bytes: bytes,
    file_path: str,
    *,
    container=None,
) -> list[Chunk]:
    if node.type in {"export_statement", "export_default_declaration"}:
        declaration = node.child_by_field_name("declaration")
        if declaration is None:
            return []
        return _extract_from_node(
            declaration,
            source_bytes,
            file_path,
            container=node,
        )

    statement = container or node

    if node.type in {"function_declaration", "generator_function_declaration"}:
        name = _node_text(node.child_by_field_name("name"), source_bytes)
        if not name:
            return []
        return [_chunk_from_node(statement, source_bytes, file_path, name)]

    if node.type in {"lexical_declaration", "variable_declaration"}:
        chunks: list[Chunk] = []
        for declarator in node.named_children:
            if declarator.type != "variable_declarator":
                continue
            value = declarator.child_by_field_name("value")
            if value is None or value.type not in {"function_expression", "arrow_function"}:
                continue
            name = _node_text(declarator.child_by_field_name("name"), source_bytes)
            if not name:
                continue
            chunks.append(_chunk_from_node(statement, source_bytes, file_path, name))
        return chunks

    if node.type == "class_declaration":
        class_name = _node_text(node.child_by_field_name("name"), source_bytes)
        body = node.child_by_field_name("body")
        if not class_name or body is None:
            return []

        chunks: list[Chunk] = []
        for child in body.named_children:
            if child.type != "method_definition":
                continue
            method_name = _node_text(child.child_by_field_name("name"), source_bytes)
            if not method_name:
                continue
            chunks.append(
                _chunk_from_node(child, source_bytes, file_path, f"{class_name}.{method_name}")
            )
        return chunks

    return []


def _chunk_from_node(node, source_bytes: bytes, file_path: str, function_name: str) -> Chunk:
    docstring = _leading_jsdoc(source_bytes, node.start_byte)
    return Chunk(
        code=source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace"),
        file=file_path,
        function_name=function_name,
        start_line=node.start_point.row + 1,
        end_line=node.end_point.row + 1,
        docstring=docstring,
    )


def _leading_jsdoc(source_bytes: bytes, start_byte: int) -> str | None:
    prefix = source_bytes[:start_byte]
    trimmed = prefix.rstrip(_WHITESPACE)
    if not trimmed.endswith(b"*/"):
        return None

    comment_end = len(trimmed)
    comment_start = trimmed.rfind(b"/**", 0, comment_end)
    if comment_start == -1:
        return None

    block = trimmed[comment_start:comment_end].decode("utf-8", errors="replace")
    return _normalize_jsdoc(block)


def _normalize_jsdoc(block: str) -> str | None:
    inner = block[3:-2].strip()
    if not inner:
        return None

    lines: list[str] = []
    for raw_line in inner.splitlines():
        line = raw_line.strip()
        if line.startswith("*"):
            line = line[1:].lstrip()
        lines.append(line)

    text = "\n".join(lines).strip()
    return text or None


def _node_text(node, source_bytes: bytes) -> str | None:
    if node is None:
        return None
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
