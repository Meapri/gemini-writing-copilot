#!/usr/bin/env python3
"""Run a writing-only Gemini request and print only the generated text."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "vendor"))

from gemini_web_minimal import (
    GeminiWebClient,
    GeminiWebError,
    build_writing_prompt,
    find_agy,
    load_cookie_file,
    redact_secrets,
    run_antigravity_print,
)
from gemini_web_minimal.cookies import missing_required_cookies
from gemini_web_minimal.settings import load_settings


TASKS = ("draft", "rewrite", "polish", "summarize", "translate", "outline", "custom")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or improve writing with Gemini.")
    parser.add_argument("--task", choices=TASKS, default="custom")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--source-file")
    parser.add_argument("--source-text", default="")
    parser.add_argument("--context", default="")
    parser.add_argument("--tone", default="")
    parser.add_argument("--audience", default="")
    parser.add_argument("--target-language", default="")
    parser.add_argument("--length", default="")
    parser.add_argument("--style-guide", default="")
    parser.add_argument("--variants", type=int, default=1)
    parser.add_argument("--format", dest="output_format", default="")
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


def validate_prompt_inputs(args: argparse.Namespace, source_text: str) -> None:
    if any([args.instruction.strip(), source_text.strip(), args.context.strip()]):
        return
    raise SystemExit(
        "Nothing to send to Gemini. Provide --instruction, --source-text, --source-file, or --context."
    )


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
        validate_prompt_inputs(args, source_text)
        prompt = build_writing_prompt(
            task=args.task,
            instruction=args.instruction,
            source_text=source_text,
            context=args.context,
            tone=args.tone,
            audience=args.audience,
            target_language=args.target_language,
            output_format=args.output_format,
            style_guide=args.style_guide,
            length=args.length,
            variants=args.variants,
        )

        mock_response = os.environ.get("GEMINI_WRITING_MOCK_RESPONSE")
        if mock_response is not None:
            print(mock_response)
            return 0

        settings = load_settings()
        provider = resolve_provider(args, settings)
        if provider == "antigravity":
            if args.model or args.think is not None:
                print(
                    "Antigravity provider uses the model configured in agy; --model and --think are ignored.",
                    file=sys.stderr,
                )
            print(
                run_antigravity_print(
                    prompt,
                    timeout_sec=settings.timeout_sec,
                    agy_bin=settings.agy_bin,
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
        print(generate_with_optional_relogin(client, prompt, args))
        return 0
    except (GeminiWebError, OSError, ValueError, SystemExit) as exc:
        message = str(exc)
        if isinstance(exc, SystemExit):
            code = exc.code if isinstance(exc.code, int) else 2
            message = str(exc) if str(exc) else "invalid arguments"
        else:
            code = 1
        print(redact_secrets(message), file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
