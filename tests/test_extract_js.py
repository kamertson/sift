from __future__ import annotations

from pathlib import Path

from sift.extract_js import extract_js_chunks, extract_js_chunks_from_file

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_repo_js"


def test_extract_js_chunks_from_js_fixture() -> None:
    source = (FIXTURES / "basic.js").read_text(encoding="utf-8")

    chunks = extract_js_chunks(source, "basic.js")

    assert [chunk.function_name for chunk in chunks] == ["add", "square", "Greeter.greet"]
    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(4, 6), (8, 10), (16, 18)]
    assert chunks[0].docstring == "Add two numbers."
    assert chunks[1].docstring is None
    assert chunks[2].docstring == "Say hello."


def test_extract_js_chunks_from_ts_fixture() -> None:
    chunks = extract_js_chunks_from_file(FIXTURES / "typed.ts", relative_to=FIXTURES)

    assert [chunk.function_name for chunk in chunks] == ["double", "Counter.increment"]
    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(4, 6), (12, 14)]
    assert chunks[0].docstring == "Double a number."
    assert chunks[1].docstring == "Increment the count."


def test_extract_js_chunks_from_invalid_file_returns_empty_list(tmp_path: Path) -> None:
    broken = tmp_path / "broken.js"
    broken.write_text("function broken( {\n", encoding="utf-8")

    assert extract_js_chunks_from_file(broken, relative_to=tmp_path) == []
