from __future__ import annotations

from pathlib import Path

from sift.language import extract_chunks_for_file

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_repo_js"


def test_extract_chunks_for_file_routes_js_files() -> None:
    chunks = extract_chunks_for_file(FIXTURES / "component.jsx", relative_to=FIXTURES)

    assert [chunk.function_name for chunk in chunks] == ["Widget", "noop"]
