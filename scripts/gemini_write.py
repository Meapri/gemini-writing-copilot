#!/usr/bin/env python3
"""Run a writing-only Gemini request and print only the generated text."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "vendor"))

from gemini_web_minimal import (
    GeminiWebClient,
    GeminiWebError,
    build_writing_prompt,
    collect_project_context,
    defaults_for_task,
    find_agy,
    friendly_error_message,
    infer_task,
    load_cookie_file,
    redact_secrets,
    review_output,
    run_antigravity_print,
)
from gemini_web_minimal.cookies import missing_required_cookies
from gemini_web_minimal.project_context import resolve_project_context_mode
from gemini_web_minimal.quality import resolve_quality_gate
from gemini_web_minimal.settings import load_settings
from gemini_web_minimal.writing_templates import TASK_TEMPLATES
from gemini_web_minimal.writing_guidance import (
    OUTPUT_MODE_GUIDANCE,
    PRESERVE_VOICE_GUIDANCE,
    REWRITE_STRENGTH_GUIDANCE,
    STRUCTURE_MODE_GUIDANCE,
    TASK_LABELS,
)


TASKS = tuple(TASK_LABELS)
PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
BUILTIN_PROFILE_DIR = PLUGIN_ROOT / "profiles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or improve writing with Gemini.")
    parser.add_argument("--task", choices=TASKS, default="auto")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--source-file")
    parser.add_argument("--source-text", default="")
    parser.add_argument("--context", default="")
    parser.add_argument("--tone", default="")
    parser.add_argument("--audience", default="")
    parser.add_argument("--target-language", default="")
    parser.add_argument("--length", default="")
    parser.add_argument("--style-guide", default="")
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--profile-dir", default="")
    parser.add_argument("--variants", type=int)
    parser.add_argument("--output-mode", choices=tuple(OUTPUT_MODE_GUIDANCE))
    parser.add_argument("--preserve-voice", choices=tuple(PRESERVE_VOICE_GUIDANCE))
    parser.add_argument(
        "--structure",
        dest="structure_mode",
        choices=tuple(STRUCTURE_MODE_GUIDANCE),
    )
    parser.add_argument("--rewrite-strength", choices=tuple(REWRITE_STRENGTH_GUIDANCE))
    parser.add_argument("--format", dest="output_format", default="")
    parser.add_argument("--project-context", choices=("off", "auto", "git-summary", "git-diff"))
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--max-project-context-chars", type=int)
    parser.add_argument("--quality-gate", choices=("off", "auto", "warn", "block"))
    parser.add_argument("--strict-source", choices=("auto", "off", "on"), default="auto")
    parser.add_argument("--template-mode", choices=("off", "auto", "strict"))
    parser.add_argument("--no-auto-profile", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--think", type=int)
    parser.add_argument("--provider", choices=("antigravity", "web", "auto"))
    parser.add_argument(
        "--auto-login",
        action="store_true",
        help="Gemini Web fallback only: open an independent login window if the cookie file is missing.",
    )
    parser.add_argument("--auto-login-mode", choices=("standalone", "chrome-profile"), default="standalone")
    parser.add_argument("--login-timeout", type=int, default=300)
    return parser.parse_args()


def read_source_text(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.source_text:
        chunks.append(args.source_text)
    if args.source_file:
        source_path = Path(args.source_file).expanduser()
        chunks.append(source_path.read_text(encoding="utf-8"))
    return "\n\n".join(chunk for chunk in chunks if chunk)


def validate_prompt_inputs(args: argparse.Namespace, source_text: str, context: str = "") -> None:
    if any([args.instruction.strip(), source_text.strip(), args.context.strip(), context.strip()]):
        return
    raise SystemExit(
        "Nothing to send to Gemini. Provide --instruction, --source-text, --source-file, --context, "
        "or run a source-sensitive task inside a git project with --project-context enabled."
    )


def _profile_filenames(name: str) -> list[str]:
    if not PROFILE_NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid profile name: {name}")
    return [name] if name.endswith(".md") else [name, f"{name}.md"]


def load_style_profile(name: str, *, user_profile_dir: Path) -> str:
    for base_dir in (user_profile_dir, BUILTIN_PROFILE_DIR):
        for filename in _profile_filenames(name):
            candidate = base_dir / filename
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"Writing style profile not found: {name}")


def build_style_guide(args: argparse.Namespace, settings) -> str:
    profile_dir = Path(args.profile_dir).expanduser() if args.profile_dir else settings.style_profile_dir
    sections: list[str] = []
    for profile_name in args.profile:
        profile_text = load_style_profile(profile_name, user_profile_dir=profile_dir)
        sections.append(f"Profile {profile_name}:\n{profile_text}")
    if args.style_guide.strip():
        sections.append(args.style_guide.strip())
    return "\n\n".join(sections)


def apply_routing_defaults(args: argparse.Namespace, source_text: str) -> str:
    task = infer_task(
        requested_task=args.task,
        instruction=args.instruction,
        source_text=source_text,
        context=args.context,
    )
    defaults = defaults_for_task(task)
    args.task = task
    if not args.profile and not args.no_auto_profile:
        args.profile = list(defaults.profiles)
    if args.output_mode is None:
        args.output_mode = defaults.output_mode
    if args.preserve_voice is None:
        args.preserve_voice = defaults.preserve_voice
    if args.structure_mode is None:
        args.structure_mode = defaults.structure_mode
    if args.rewrite_strength is None:
        args.rewrite_strength = defaults.rewrite_strength
    return task


def build_project_context(args: argparse.Namespace, settings, task: str) -> str:
    requested = args.project_context or settings.project_context
    mode = resolve_project_context_mode(task, requested)
    if mode == "off":
        return ""
    max_chars = args.max_project_context_chars or settings.max_project_context_chars
    try:
        return collect_project_context(
            root=Path(args.project_root),
            mode=mode,
            max_chars=max(1000, int(max_chars)),
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"Project context collection skipped: {redact_secrets(exc)}", file=sys.stderr)
        return ""


def template_argument(args: argparse.Namespace, settings, task: str) -> str | None:
    mode = args.template_mode or settings.template_mode
    if mode == "off":
        return None
    if mode == "strict" or task in TASK_TEMPLATES:
        return ""
    return None


def should_use_strict_source(args: argparse.Namespace, task: str, gate: str, project_context: str, source_text: str) -> bool:
    if args.strict_source == "on":
        return True
    if args.strict_source == "off":
        return False
    return gate != "off" and bool(project_context or source_text or task in {"summarize", "translate"})


def emit_quality_warnings(result: str, *, args: argparse.Namespace, source_text: str, context: str, task: str) -> str:
    has_source_context = bool(source_text.strip() or context.strip())
    gate = resolve_quality_gate(task, args.quality_gate or "auto", has_source_context)
    report = review_output(text=result, source_text=source_text, context=context, task=task)
    if gate == "off" or not report.issues:
        return report.text
    for issue in report.issues:
        print(f"Quality warning: {issue}", file=sys.stderr)
    if gate == "block":
        raise GeminiWebError("Gemini output did not pass the writing quality gate.")
    return report.text


def cookie_ready(cookie_file: Path) -> bool:
    if not cookie_file.exists():
        return False
    try:
        cookie_data = load_cookie_file(cookie_file)
    except Exception:
        return False
    return not missing_required_cookies(cookie_data.values)


def ensure_login_if_requested(args: argparse.Namespace, *, force: bool = False) -> None:
    settings = load_settings()
    auto_login = args.auto_login or os.environ.get("GEMINI_WRITING_AUTO_LOGIN", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not force and cookie_ready(settings.cookie_file):
        return
    if not auto_login:
        return
    command = "login-standalone" if args.auto_login_mode == "standalone" else "login-chrome"
    cmd = [
        sys.executable,
        str(PLUGIN_ROOT / "scripts" / "gemini_login.py"),
        command,
        "--skip-smoke",
        "--timeout",
        str(args.login_timeout),
    ]
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise GeminiWebError("Gemini login was not completed.")


def resolve_provider(args: argparse.Namespace, settings) -> str:
    provider = (args.provider or settings.provider or "antigravity").lower()
    if provider == "auto":
        return "antigravity" if find_agy(settings.agy_bin) else "web"
    return provider


def generate_with_optional_relogin(client: GeminiWebClient, prompt: str, args: argparse.Namespace) -> str:
    try:
        return client.generate(prompt)
    except GeminiWebError as exc:
        auto_login = args.auto_login or os.environ.get("GEMINI_WRITING_AUTO_LOGIN", "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not auto_login or exc.status not in {401, 403}:
            raise
        ensure_login_if_requested(
            argparse.Namespace(
                auto_login=True,
                auto_login_mode=args.auto_login_mode,
                login_timeout=args.login_timeout,
            ),
            force=True,
        )
        return client.generate(prompt)


def main() -> int:
    args = parse_args()
    try:
        source_text = read_source_text(args)
        settings = load_settings()
        args.project_context = args.project_context or settings.project_context
        args.quality_gate = args.quality_gate or settings.quality_gate
        args.template_mode = args.template_mode or settings.template_mode
        task = apply_routing_defaults(args, source_text)
        project_context = build_project_context(args, settings, task)
        combined_context = "\n\n".join(part for part in (args.context, project_context) if part.strip())
        validate_prompt_inputs(args, source_text, combined_context)
        gate = resolve_quality_gate(task, args.quality_gate, bool(source_text or combined_context))
        variants = args.variants
        if variants is None:
            variants = 3 if args.output_mode == "alternatives" else 1
        prompt = build_writing_prompt(
            task=task,
            instruction=args.instruction,
            source_text=source_text,
            context=args.context,
            tone=args.tone,
            audience=args.audience,
            target_language=args.target_language,
            output_format=args.output_format,
            style_guide=build_style_guide(args, settings),
            length=args.length,
            variants=variants,
            output_mode=args.output_mode,
            preserve_voice=args.preserve_voice,
            structure_mode=args.structure_mode,
            rewrite_strength=args.rewrite_strength,
            task_template=template_argument(args, settings, task),
            project_context=project_context,
            strict_source=should_use_strict_source(args, task, gate, project_context, source_text),
        )

        mock_response = os.environ.get("GEMINI_WRITING_MOCK_RESPONSE")
        if mock_response is not None:
            print(
                emit_quality_warnings(
                    mock_response,
                    args=args,
                    source_text=source_text,
                    context=combined_context,
                    task=task,
                )
            )
            return 0

        provider = resolve_provider(args, settings)
        if provider == "antigravity":
            if args.model or args.think is not None:
                print(
                    "Antigravity provider uses the model configured in agy; --model and --think are ignored.",
                    file=sys.stderr,
                )
            result = run_antigravity_print(
                prompt,
                timeout_sec=settings.timeout_sec,
                agy_bin=settings.agy_bin,
            )
            print(
                emit_quality_warnings(
                    result,
                    args=args,
                    source_text=source_text,
                    context=combined_context,
                    task=task,
                )
            )
            return 0

        ensure_login_if_requested(args)
        client = GeminiWebClient(
            cookie_file=str(settings.cookie_file),
            model=args.model or settings.model,
            think=args.think if args.think is not None else settings.think,
            timeout_sec=settings.timeout_sec,
            retry_attempts=settings.retry_attempts,
            retry_delay_sec=settings.retry_delay_sec,
            proxy=settings.proxy,
        )
        result = generate_with_optional_relogin(client, prompt, args)
        print(
            emit_quality_warnings(
                result,
                args=args,
                source_text=source_text,
                context=combined_context,
                task=task,
            )
        )
        return 0
    except (GeminiWebError, OSError, ValueError, SystemExit) as exc:
        message = str(exc)
        if isinstance(exc, SystemExit):
            code = exc.code if isinstance(exc.code, int) else 2
            message = str(exc) if str(exc) else "invalid arguments"
        else:
            code = 1
        print(redact_secrets(friendly_error_message(message)), file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
