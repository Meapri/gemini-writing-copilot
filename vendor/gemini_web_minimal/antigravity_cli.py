"""Antigravity CLI provider for writing-only calls.

The plugin intentionally delegates login, refresh, account selection, and
token storage to the official Antigravity CLI (`agy`). This avoids reading
Chrome cookies, touching macOS Keychain, or depending on the Gemini CLI.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
import re
import shutil
import subprocess

from .errors import GeminiWebError
from .redaction import redact_secrets

DEFAULT_ANTIGRAVITY_TOKEN_FILE = Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
DEFAULT_ANTIGRAVITY_SETTINGS_FILE = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def antigravity_token_file() -> Path:
    override = os.environ.get("HERMES_ANTIGRAVITY_CLI_TOKEN_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_ANTIGRAVITY_TOKEN_FILE


def antigravity_settings_file() -> Path:
    override = os.environ.get("GEMINI_WRITING_ANTIGRAVITY_SETTINGS_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_ANTIGRAVITY_SETTINGS_FILE


def selected_antigravity_model() -> str:
    path = antigravity_settings_file()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    model = data.get("model") if isinstance(data, dict) else ""
    return str(model or "").strip()


def find_agy(binary: str | None = None) -> str | None:
    candidate = (binary or os.environ.get("GEMINI_WRITING_AGY_BIN", "") or "agy").strip()
    if not candidate:
        candidate = "agy"
    if "/" in candidate:
        path = Path(candidate).expanduser()
        return str(path) if path.exists() and os.access(path, os.X_OK) else None
    return shutil.which(candidate)


def clean_antigravity_output(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return ANSI_RE.sub("", normalized).strip()


def _print_timeout(timeout_sec: int) -> str:
    return f"{max(1, int(timeout_sec))}s"


def run_antigravity_print(
    prompt: str,
    *,
    timeout_sec: int,
    agy_bin: str | None = None,
) -> str:
    if not prompt.strip():
        raise ValueError("Antigravity prompt is empty.")

    agy = find_agy(agy_bin)
    if not agy:
        raise GeminiWebError(
            "Antigravity CLI (`agy`) was not found. Install or open Google Antigravity first, "
            "or set GEMINI_WRITING_AGY_BIN to the agy binary path."
        )

    command = [agy, "--print", prompt, "--print-timeout", _print_timeout(timeout_sec)]
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    try:
        proc = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=max(int(timeout_sec) + 30, 60),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        details = clean_antigravity_output((exc.stdout or "") + "\n" + (exc.stderr or ""))
        suffix = f" Last output: {redact_secrets(details)}" if details else ""
        raise GeminiWebError(
            "Antigravity did not finish before the timeout. If a Google login window is open, "
            "complete that login and retry, or increase GEMINI_WRITING_TIMEOUT_SEC."
            + suffix
        ) from exc

    stdout = clean_antigravity_output(proc.stdout)
    stderr = clean_antigravity_output(proc.stderr)
    if proc.returncode != 0:
        detail = stderr or stdout or f"exit code {proc.returncode}"
        raise GeminiWebError(f"Antigravity CLI request failed: {redact_secrets(detail)}")
    if not stdout:
        detail = f" stderr: {redact_secrets(stderr)}" if stderr else ""
        raise GeminiWebError(f"Antigravity CLI returned an empty response.{detail}")
    return stdout
