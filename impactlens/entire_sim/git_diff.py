"""Extracts changed files + changed line ranges from a git commit."""

from __future__ import annotations
import subprocess
import re


class GitError(Exception):
    """Raised for user-actionable git failures (bad ref, not a repo, etc.)."""


def _run(repo_path: str, *args) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, *args],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        raise GitError("git is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        raise GitError(f"git {' '.join(args)} timed out")
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GitError(f"git {' '.join(args)} failed: {stderr or 'unknown error'}")
    return result.stdout


def commit_exists(repo_path: str, commit: str) -> bool:
    try:
        _run(repo_path, "cat-file", "-e", f"{commit}^{{commit}}")
        return True
    except GitError:
        return False


def get_commit_message(repo_path: str, commit: str) -> str:
    return _run(repo_path, "log", "-1", "--pretty=%B", commit).strip()


def get_commit_meta(repo_path: str, commit: str) -> dict:
    out = _run(repo_path, "log", "-1", "--pretty=%H|%an|%ae|%ad|%s", commit).strip()
    sha, author, email, date, subject = out.split("|", 4)
    return {"sha": sha, "author": author, "email": email, "date": date, "subject": subject}


def get_changed_files(repo_path: str, commit: str) -> list[str]:
    out = _run(repo_path, "show", "--name-only", "--pretty=format:", commit)
    return [line.strip() for line in out.splitlines() if line.strip()]


_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def get_changed_line_ranges(repo_path: str, commit: str) -> dict[str, list[tuple[int, int]]]:
    """
    Returns {file_path: [(start_line, end_line), ...]} for lines touched
    in the *new* version of each file at this commit (added/modified lines).
    """
    diff = _run(repo_path, "show", "--unified=0", commit)
    ranges: dict[str, list[tuple[int, int]]] = {}
    current_file = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[len("+++ b/"):]
        elif line.startswith("@@") and current_file:
            m = _HUNK_RE.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) else 1
                if count == 0:
                    continue
                ranges.setdefault(current_file, []).append((start, start + count - 1))
    return ranges


def get_full_diff(repo_path: str, commit: str) -> str:
    return _run(repo_path, "show", commit)
