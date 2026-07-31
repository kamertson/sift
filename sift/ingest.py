"""Discover source files in a local path or git repository."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from git import InvalidGitRepositoryError, Repo

# Directories skipped during walk even without a .gitignore entry.
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "node_modules",
        "migrations",
        "dist",
        "build",
        ".eggs",
        "eggs",
        "site-packages",
    }
)


def ingest(path: str | Path, languages: set[str] | None = None) -> tuple[Path, list[Path]]:
    """Resolve *path* and return ``(root, python_files)``.

    Walks the target directory, finds files matching the requested language
    set, skips common junk directories, and respects ``.gitignore`` patterns
    when present.

    If *path* points at a git working tree, files reported by ``git ls-files``
    are preferred (already gitignore-aware). Otherwise a filesystem walk with
    local ``.gitignore`` matching is used.

    Args:
        path: Local directory to scan.

    Returns:
        A tuple of the resolved root directory and a sorted list of absolute
        paths to source files under that root.
    """
    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root}")

    suffixes = _language_suffixes(languages)
    if not suffixes:
        return root, []

    try:
        files = _ingest_via_git(root, suffixes)
    except InvalidGitRepositoryError:
        files = _ingest_via_walk(root, suffixes)

    return root, sorted(files)


def _ingest_via_git(root: Path, suffixes: set[str]) -> list[Path]:
    """List tracked files matching *suffixes* via GitPython."""
    repo = Repo(root, search_parent_directories=True)
    # Ensure we only return files under the requested root even if Repo
    # discovered a parent git directory.
    repo_root = Path(repo.working_tree_dir or root).resolve()

    # Tracked files only — matches what gitignore would leave visible.
    patterns = [f"*{suffix}" for suffix in sorted(suffixes)]
    relative_paths = repo.git.ls_files("--", *patterns).splitlines()
    files: list[Path] = []
    for rel in relative_paths:
        if not rel:
            continue
        abs_path = (repo_root / rel).resolve()
        try:
            abs_path.relative_to(root)
        except ValueError:
            continue
        if _is_under_skipped_dir(abs_path, root):
            continue
        if abs_path.is_file():
            files.append(abs_path)
    return files


def _ingest_via_walk(root: Path, suffixes: set[str]) -> list[Path]:
    """Walk the filesystem, applying skip dirs and ``.gitignore`` patterns."""
    gitignore_patterns = _load_gitignore_patterns(root)
    files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune junk directories in-place so os.walk skips them.
        current = Path(dirpath)
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIR_NAMES and not _is_ignored(current / d, root, gitignore_patterns)
        ]

        for name in filenames:
            if Path(name).suffix not in suffixes:
                continue
            path = current / name
            if _is_ignored(path, root, gitignore_patterns):
                continue
            files.append(path.resolve())

    return files


def _is_under_skipped_dir(path: Path, root: Path) -> bool:
    """Return True if any path component under *root* is a skipped directory."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part in SKIP_DIR_NAMES for part in relative.parts)


def _load_gitignore_patterns(root: Path) -> list[str]:
    """Load simple gitignore patterns from ``root/.gitignore`` if it exists."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []

    patterns: list[str] = []
    for raw in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            # Negation patterns are out of scope for this MVP matcher.
            continue
        patterns.append(line)
    return patterns


def _is_ignored(path: Path, root: Path, patterns: list[str]) -> bool:
    """Return True if *path* matches any loaded gitignore-style pattern."""
    if not patterns:
        return False

    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return False

    name = path.name
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if normalized.startswith("/"):
            candidate = normalized.lstrip("/")
            if relative == candidate or relative.startswith(candidate + "/"):
                return True
            if fnmatch.fnmatch(relative, candidate):
                return True
            continue

        if fnmatch.fnmatch(name, normalized) or fnmatch.fnmatch(relative, normalized):
            return True
        if fnmatch.fnmatch(relative, f"**/{normalized}"):
            return True
        # Directory-style patterns: match the path prefix.
        if relative == normalized or relative.startswith(normalized + "/"):
            return True

    return False


def _language_suffixes(languages: set[str] | None) -> set[str]:
    """Return the set of file suffixes associated with *languages*."""
    requested = languages or {"python"}
    suffixes: set[str] = set()
    mapping = {
        "python": {".py"},
        "javascript": {".js", ".jsx"},
        "typescript": {".ts", ".tsx"},
    }
    for language in requested:
        suffixes.update(mapping.get(language, set()))
    return suffixes
