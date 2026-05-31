#!/usr/bin/env python3
"""Diagnose local Gemini Writing Copilot configuration."""

from __future__ import annotations

from pathlib import Path
import ssl
import stat
import sys
import urllib.error
import urllib.request

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "vendor"))

from gemini_web_minimal import (
    GeminiWebClient,
    GeminiWebError,
    antigravity_token_file,
    find_agy,
    load_cookie_file,
    redact_secrets,
    run_antigravity_print,
    selected_antigravity_model,
)
from gemini_web_minimal.cookies import missing_required_cookies
from gemini_web_minimal.settings import load_settings


def check_network(proxy: str | None, timeout: int) -> tuple[bool, str]:
    req = urllib.request.Request(
        "https://gemini.google.com/app",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        if proxy:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy, "https": proxy}),
                urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            )
            opener.open(req, timeout=timeout).close()
        else:
            urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=timeout).close()
        return True, "reachable"
    except Exception as exc:  # noqa: BLE001 - diagnostics should report concrete transport failures.
        return False, redact_secrets(exc)


def main() -> int:
    settings = load_settings()
    failures = 0

    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 9):
        print("Python check: requires 3.9+")
        failures += 1
    else:
        print("Python check: ok")

    print(f"Config file: {settings.config_file}")
    print(f"Provider: {settings.provider}")
    print(f"Antigravity CLI: {find_agy(settings.agy_bin) or 'not found'}")
    print(f"Antigravity model: {selected_antigravity_model() or 'unknown'}")
    token_status = "present" if antigravity_token_file().exists() else "not found; agy may use another local store"
    print(f"Antigravity token file: {token_status}")
    print(f"Cookie file: {settings.cookie_file}")
    print(f"Gemini Web fallback model: {settings.model}")
    print(f"Think: {settings.think if settings.think is not None else 'model default'}")
    print(f"Proxy: {'configured' if settings.proxy else 'not configured'}")
    print(f"Project context: {settings.project_context}")
    print(f"Quality gate: {settings.quality_gate}")
    print(f"Template mode: {settings.template_mode}")

    provider = settings.provider
    if provider == "auto":
        provider = "antigravity" if find_agy(settings.agy_bin) else "web"
        print(f"Resolved provider: {provider}")

    if provider == "antigravity":
        if not find_agy(settings.agy_bin):
            print("Antigravity check: agy not found")
            failures += 1
        else:
            try:
                result = run_antigravity_print(
                    "Reply with exactly: OK",
                    timeout_sec=min(settings.timeout_sec, 60),
                    agy_bin=settings.agy_bin,
                )
                if result.strip() == "OK":
                    print("Antigravity generation check: ok")
                else:
                    print("Antigravity generation check: unexpected response")
                    failures += 1
            except GeminiWebError as exc:
                print(redact_secrets(f"Antigravity generation check: failed ({exc})"))
                failures += 1
        return 0 if failures == 0 else 1

    if settings.cookie_file.exists():
        mode = stat.S_IMODE(settings.cookie_file.stat().st_mode)
        print(f"Cookie mode: {oct(mode)}")
        if mode != 0o600:
            print("Cookie permission check: expected 0600")
            failures += 1
        try:
            cookie_data = load_cookie_file(settings.cookie_file)
            missing = missing_required_cookies(cookie_data.values)
            if missing:
                print("Cookie content check: incomplete (" + ", ".join(missing) + ")")
                failures += 1
            else:
                print("Cookie content check: ok")
        except Exception as exc:  # noqa: BLE001
            print(redact_secrets(f"Cookie content check: failed ({exc})"))
            failures += 1
    else:
        print("Cookie check: missing. Run scripts/gemini_login.py start, then finish.")
        failures += 1

    ok, message = check_network(settings.proxy, min(settings.timeout_sec, 30))
    print(f"Network check: {message}")
    if not ok:
        failures += 1

    if settings.cookie_file.exists():
        try:
            client = GeminiWebClient(
                cookie_file=str(settings.cookie_file),
                model=settings.model,
                think=settings.think,
                timeout_sec=min(settings.timeout_sec, 60),
                retry_attempts=1,
                retry_delay_sec=0,
                proxy=settings.proxy,
            )
            client.generate("Reply with exactly: OK")
            print("Gemini generation check: ok")
        except GeminiWebError as exc:
            print(redact_secrets(f"Gemini generation check: failed ({exc})"))
            failures += 1

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
