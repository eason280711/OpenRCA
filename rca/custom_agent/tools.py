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


def read_file(file_path: str, start_line: int = 1, max_lines: int = 200) -> str:
    """Read a slice of a text file and return JSON."""
    target = _resolve_path(file_path)
    if not target.exists():
        return json.dumps({"error": f"File not found: {file_path}", "lines": []})
    if target.is_dir():
        return json.dumps({"error": f"Path is a directory: {file_path}", "lines": []})

    if start_line < 1:
        return json.dumps({"error": "start_line must be >= 1", "lines": []})
    if max_lines < 1:
        return json.dumps({"error": "max_lines must be >= 1", "lines": []})

    lines = []
    end_line = start_line - 1
    with target.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            if line_no < start_line:
                continue
            lines.append(line.rstrip("\n"))
            end_line = line_no
            if len(lines) >= max_lines:
                break

    return json.dumps(
        {
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "lines": lines,
            "truncated": len(lines) >= max_lines,
        }
    )


def grep_log(
    log_file: str,
    keyword: str,
    context_lines: int = 2,
    max_matches: int = 15,
) -> str:
    """Search keyword in a log file and return JSON context."""
    target = _resolve_path(log_file)
    if not target.exists():
        return json.dumps({"error": f"File not found: {log_file}", "matches": []})
    if target.is_dir():
        return json.dumps({"error": f"Path is a directory: {log_file}", "matches": []})
    if context_lines < 0:
        return json.dumps({"error": "context_lines must be >= 0", "matches": []})

    matches = []
    pending = []
    keyword_lower = keyword.lower()
    before_buffer = []

    with target.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.rstrip("\n")
            if keyword_lower in stripped.lower():
                context = before_buffer + [stripped]
                pending.append(
                    {
                        "line_number": line_no,
                        "context": context,
                        "matched_line": stripped,
                        "remaining": context_lines,
                    }
                )

            for match in list(pending):
                if match["remaining"] > 0 and match["line_number"] != line_no:
                    match["context"].append(stripped)
                    match["remaining"] -= 1
                if match["remaining"] == 0:
                    matches.append(
                        {
                            "line_number": match["line_number"],
                            "context": match["context"],
                            "matched_line": match["matched_line"],
                        }
                    )
                    pending.remove(match)
                    if len(matches) >= max_matches:
                        pending.clear()
                        break

            if len(matches) >= max_matches:
                break

            before_buffer.append(stripped)
            if len(before_buffer) > context_lines:
                before_buffer.pop(0)

    return json.dumps(
        {
            "keyword": keyword,
            "total_matches": len(matches),
            "matches": matches,
            "truncated": len(matches) >= max_matches,
        }
    )


TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "grep_log": grep_log,
}
