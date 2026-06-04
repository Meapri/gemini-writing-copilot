#!/usr/bin/env python3
"""Minimal MCP stdio server for Gemini Writing Copilot."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, Iterable, List


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WRITER = PLUGIN_ROOT / "scripts" / "gemini_write.py"
SERVER_NAME = "gemini-writing-copilot"
SERVER_VERSION = "0.3.0"


TASKS = (
    "auto",
    "draft",
    "rewrite",
    "polish",
    "summarize",
    "translate",
    "outline",
    "email",
    "announcement",
    "blog",
    "pr-description",
    "release-notes",
    "readme",
    "proposal",
    "product-copy",
    "technical-doc",
    "custom",
)


TOOL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "enum": list(TASKS),
            "default": "auto",
            "description": "Writing task to run. Use auto when the prompt has enough signal.",
        },
        "instruction": {
            "type": "string",
            "description": "User-facing writing instruction, such as the rewrite goal or desired output.",
        },
        "source_text": {
            "type": "string",
            "description": "Draft text, notes, or source material to rewrite, polish, summarize, or translate.",
        },
        "source_file": {
            "type": "string",
            "description": "Optional local source file path to pass to the writer.",
        },
        "context": {
            "type": "string",
            "description": "Additional factual context that Gemini should preserve.",
        },
        "tone": {"type": "string", "description": "Desired tone or voice."},
        "audience": {"type": "string", "description": "Target reader or audience."},
        "target_language": {"type": "string", "description": "Target language for translation tasks."},
        "length": {"type": "string", "description": "Desired length or density."},
        "style_guide": {"type": "string", "description": "House style or do/don't guidance."},
        "profile": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Bundled or user style profiles. Values are passed as repeated --profile flags.",
        },
        "variants": {"type": "integer", "minimum": 1, "maximum": 5},
        "output_mode": {
            "type": "string",
            "enum": ["final", "alternatives", "edit-with-notes", "diff-summary"],
        },
        "preserve_voice": {
            "type": "string",
            "enum": ["off", "light", "medium", "strong"],
        },
        "structure": {
            "type": "string",
            "enum": ["preserve", "allow-restructure", "restructure"],
        },
        "rewrite_strength": {
            "type": "string",
            "enum": ["light", "medium", "heavy", "high"],
        },
        "format": {"type": "string", "description": "Output format guidance."},
        "project_context": {
            "type": "string",
            "enum": ["off", "auto", "git-summary", "git-diff"],
        },
        "project_root": {"type": "string", "description": "Project root used for git context."},
        "max_project_context_chars": {"type": "integer", "minimum": 1000},
        "quality_gate": {"type": "string", "enum": ["off", "auto", "warn", "block"]},
        "strict_source": {"type": "string", "enum": ["auto", "off", "on"]},
        "template_mode": {"type": "string", "enum": ["off", "auto", "strict"]},
        "provider": {"type": "string", "enum": ["antigravity", "web", "auto"]},
        "auto_login": {
            "type": "boolean",
            "description": "Gemini Web fallback only: allow the login helper to run.",
        },
    },
    "additionalProperties": False,
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _add_text_arg(command: List[str], flag: str, value: Any) -> None:
    text = _text(value)
    if text:
        command.extend([flag, text])


def _add_choice_arg(command: List[str], flag: str, value: Any, allowed: Iterable[str]) -> None:
    text = _text(value)
    if text:
        if text not in set(allowed):
            raise ValueError(f"{flag} must be one of: {', '.join(allowed)}")
        command.extend([flag, text])


def build_writer_command(args: Dict[str, Any]) -> List[str]:
    command = [sys.executable, str(WRITER)]
    _add_choice_arg(command, "--task", args.get("task") or "auto", TASKS)
    for flag, key in (
        ("--instruction", "instruction"),
        ("--source-text", "source_text"),
        ("--source-file", "source_file"),
        ("--context", "context"),
        ("--tone", "tone"),
        ("--audience", "audience"),
        ("--target-language", "target_language"),
        ("--length", "length"),
        ("--style-guide", "style_guide"),
        ("--format", "format"),
        ("--project-root", "project_root"),
    ):
        _add_text_arg(command, flag, args.get(key))
    profiles = args.get("profile")
    if isinstance(profiles, list):
        for profile in profiles:
            _add_text_arg(command, "--profile", profile)
    elif profiles:
        raise ValueError("profile must be an array of profile names")
    if args.get("variants") is not None:
        command.extend(["--variants", str(int(args["variants"]))])
    if args.get("max_project_context_chars") is not None:
        command.extend(["--max-project-context-chars", str(int(args["max_project_context_chars"]))])
    _add_choice_arg(command, "--output-mode", args.get("output_mode"), ("final", "alternatives", "edit-with-notes", "diff-summary"))
    _add_choice_arg(command, "--preserve-voice", args.get("preserve_voice"), ("off", "light", "medium", "strong"))
    _add_choice_arg(command, "--structure", args.get("structure"), ("preserve", "allow-restructure", "restructure"))
    _add_choice_arg(command, "--rewrite-strength", args.get("rewrite_strength"), ("light", "medium", "heavy", "high"))
    _add_choice_arg(command, "--project-context", args.get("project_context"), ("off", "auto", "git-summary", "git-diff"))
    _add_choice_arg(command, "--quality-gate", args.get("quality_gate"), ("off", "auto", "warn", "block"))
    _add_choice_arg(command, "--strict-source", args.get("strict_source"), ("auto", "off", "on"))
    _add_choice_arg(command, "--template-mode", args.get("template_mode"), ("off", "auto", "strict"))
    _add_choice_arg(command, "--provider", args.get("provider"), ("antigravity", "web", "auto"))
    if bool(args.get("auto_login")):
        command.append("--auto-login")
    return command


def run_gemini_write(arguments: Dict[str, Any]) -> Dict[str, Any]:
    command = build_writer_command(arguments)
    proc = subprocess.run(command, check=False, text=True, capture_output=True)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        detail = stderr or stdout or f"exit code {proc.returncode}"
        raise RuntimeError(detail)
    return {
        "content": [{"type": "text", "text": stdout}],
        "structuredContent": {"text": stdout, "stderr": stderr, "command": [command[0], str(WRITER)]},
        "isError": False,
    }


def _tool_definition() -> Dict[str, Any]:
    return {
        "name": "gemini_write",
        "description": (
            "Draft, rewrite, polish, translate, summarize, or prepare user-facing prose "
            "with Gemini Writing Copilot. Codex should review the returned draft before publishing."
        ),
        "inputSchema": TOOL_SCHEMA,
    }


def handle_request(message: Dict[str, Any]) -> Dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
        elif method == "tools/list":
            result = {"tools": [_tool_definition()]}
        elif method == "tools/call":
            params = message.get("params") or {}
            if params.get("name") != "gemini_write":
                raise ValueError(f"unknown tool: {params.get('name')}")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            result = run_gemini_write(arguments)
        else:
            raise ValueError(f"unsupported method: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def serve() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        else:
            response = handle_request(message)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
