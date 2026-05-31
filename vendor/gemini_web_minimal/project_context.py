"""Safe local project context collection for prose tasks."""

from __future__ import annotations

from pathlib import Path
import subprocess


PROJECT_CONTEXT_TASKS = {
    "pr-description",
    "release-notes",
    "readme",
    "technical-doc",
    "proposal",
}

METADATA_FILES = (
    "README.md",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    ".codex-plugin/plugin.json",
)


def resolve_project_context_mode(task: str, requested_mode: str) -> str:
    mode = (requested_mode or "auto").lower()
    if mode == "auto":
        return "git-summary" if task in PROJECT_CONTEXT_TASKS else "off"
    return mode


def _run(command: list[str], *, cwd: Path, timeout_sec: int = 10) -> str:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _git_root(root: Path) -> Path | None:
    output = _run(["git", "rev-parse", "--show-toplevel"], cwd=root)
    if not output:
        return None
    return Path(output).expanduser()


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 80)].rstrip() + "\n[project context truncated]"


def _add_section(sections: list[str], title: str, body: str) -> None:
    body = body.strip()
    if body:
        sections.append(f"{title}:\n{body}")


def _read_metadata(root: Path, remaining_chars: int) -> str:
    sections: list[str] = []
    for relative in METADATA_FILES:
        path = root / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        budget = max(600, min(3000, remaining_chars // 2))
        _add_section(sections, relative, _clip(text, budget))
    return "\n\n".join(sections)


def collect_project_context(
    *,
    root: Path,
    mode: str,
    max_chars: int = 12000,
) -> str:
    mode = (mode or "off").lower()
    if mode == "off":
        return ""
    if mode not in {"git-summary", "git-diff"}:
        raise ValueError("project context mode must be one of: off, auto, git-summary, git-diff")

    root = root.expanduser().resolve()
    sections: list[str] = []
    git_root = _git_root(root)
    context_root = git_root or root

    if git_root:
        _add_section(sections, "Project root", str(git_root))
        _add_section(sections, "Git status", _run(["git", "status", "--short"], cwd=git_root))
        _add_section(sections, "Changed files", _run(["git", "diff", "--name-status"], cwd=git_root))
        _add_section(sections, "Staged files", _run(["git", "diff", "--cached", "--name-status"], cwd=git_root))
        _add_section(sections, "Diff stat", _run(["git", "diff", "--stat"], cwd=git_root))
        _add_section(sections, "Staged diff stat", _run(["git", "diff", "--cached", "--stat"], cwd=git_root))
        _add_section(sections, "Recent commits", _run(["git", "log", "--oneline", "-n", "8"], cwd=git_root))
        if mode == "git-diff":
            _add_section(
                sections,
                "Unstaged diff excerpt",
                _run(["git", "diff", "--no-ext-diff", "--unified=3"], cwd=git_root, timeout_sec=20),
            )
            _add_section(
                sections,
                "Staged diff excerpt",
                _run(["git", "diff", "--cached", "--no-ext-diff", "--unified=3"], cwd=git_root, timeout_sec=20),
            )
    else:
        _add_section(sections, "Project root", str(context_root))

    current = "\n\n".join(sections)
    metadata = _read_metadata(context_root, max(0, max_chars - len(current)))
    _add_section(sections, "Project metadata", metadata)
    return _clip("\n\n".join(sections), max_chars)

