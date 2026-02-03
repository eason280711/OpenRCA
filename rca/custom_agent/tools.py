"""Minimal tools for the custom OpenRCA agent."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = REPO_ROOT / "dataset"


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if path.startswith("dataset/"):
        return REPO_ROOT / path
    if path.startswith("/dataset/"):
        return REPO_ROOT / path.lstrip("/")
    return REPO_ROOT / path


def list_files(directory: str) -> str:
    """List files in a directory and return JSON."""
    target = _resolve_path(directory)
    if not target.exists():
        return json.dumps({"error": f"Directory not found: {directory}", "files": []})
    if not target.is_dir():
        return json.dumps({"error": f"Not a directory: {directory}", "files": []})
    files = [p.name for p in target.iterdir()]
    return json.dumps({"directory": str(directory), "files": files})


def read_file(file_path: str) -> str:
    """Read a text file and return its content."""
    target = _resolve_path(file_path)
    if not target.exists():
        return f"ERROR: File not found: {file_path}"
    if target.is_dir():
        return f"ERROR: Path is a directory: {file_path}"
    return target.read_text(encoding="utf-8", errors="replace")


def grep_log(log_file: str, keyword: str, context_lines: int = 2) -> str:
    """Search keyword in a log file and return JSON context."""
    content = read_file(log_file)
    if content.startswith("ERROR:"):
        return json.dumps({"error": content, "matches": []})

    lines = content.split("\n")
    matches = []

    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            matches.append(
                {
                    "line_number": i + 1,
                    "context": lines[start:end],
                    "matched_line": line,
                }
            )

    return json.dumps(
        {
            "keyword": keyword,
            "total_matches": len(matches),
            "matches": matches[:15],
        }
    )


TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "grep_log": grep_log,
}
