from __future__ import annotations

import shutil
from pathlib import Path

from sift.ingest import ingest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "sample_repo_js"


def test_ingest_includes_js_ts_files_when_requested(tmp_path: Path) -> None:
    repo = tmp_path / "sample_repo_js"
    shutil.copytree(FIXTURES, repo)

    root, files = ingest(repo, languages={"javascript", "typescript"})

    assert root == repo.resolve()
    assert sorted(path.name for path in files) == [
        "assignments.js",
        "basic.js",
        "component.jsx",
        "typed.ts",
    ]


def test_ingest_defaults_to_python_only() -> None:
    _, files = ingest(FIXTURES)

    assert files == []
