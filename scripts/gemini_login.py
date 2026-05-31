#!/usr/bin/env python3
"""Manage the dedicated Gemini Web login profile and cookie file."""

from __future__ import annotations

import argparse
import hashlib
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
import tempfile
import webbrowser

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "vendor"))

from gemini_web_minimal import GeminiWebClient, GeminiWebError, load_cookie_file, redact_secrets, write_private_json
from gemini_web_minimal.cookies import REQUIRED_COOKIE_NAMES, build_cookie_header, missing_required_cookies
from gemini_web_minimal.settings import load_settings

GEMINI_APP_URL = "https://gemini.google.com/app"
DEFAULT_CHROME_BRIDGE_PORT = 19731
CHROME_BRIDGE_DIRNAME = "chrome-cookie-bridge"
DEFAULT_CHROME_DATA_DIR = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
GEMINI_COOKIE_TARGET_HOST = "gemini.google.com"
STANDALONE_CHROME_DIRNAME = "standalone-google-login"
CHROME_EXECUTABLE_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path.home() / "Applications" / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Login helper for Gemini Writing Copilot.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start", help="Open a dedicated browser profile for Gemini login.")
    start.add_argument("--no-block", action="store_true", help="Open the browser and return immediately.")
    finish = subparsers.add_parser("finish", help="Extract and save cookies from the dedicated profile.")
    finish.add_argument("--skip-smoke", action="store_true", help="Save cookies without running a Gemini smoke test.")
    standalone = subparsers.add_parser(
        "login-standalone",
        help="Open an independent Google login window and import only that isolated session.",
    )
    standalone.add_argument("--timeout", type=int, default=300, help="Seconds to watch the standalone login profile.")
    standalone.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between cookie checks.")
    standalone.add_argument("--skip-smoke", action="store_true", help="Save cookies without running a Gemini smoke test.")
    standalone.add_argument("--keep-window", action="store_true", help="Leave the standalone Chrome window open after import.")
    direct = subparsers.add_parser(
        "import-chrome-profile",
        help="One-shot import from the normal Chrome profile using macOS Keychain decryption.",
    )
    direct.add_argument("--profile", default="", help="Chrome profile directory or display name. Defaults to auto-detect.")
    direct.add_argument("--chrome-data-dir", default="", help="Override Chrome user data directory.")
    direct.add_argument("--list-profiles", action="store_true", help="List available Chrome profiles and exit.")
    direct.add_argument("--skip-smoke", action="store_true", help="Save cookies without running a Gemini smoke test.")
    login_chrome = subparsers.add_parser(
        "login-chrome",
        help="Open Gemini in the main Chrome browser, wait for manual login, then import the profile cookies.",
    )
    login_chrome.add_argument("--profile", default="", help="Chrome profile directory or display name. Defaults to auto-detect.")
    login_chrome.add_argument("--chrome-data-dir", default="", help="Override Chrome user data directory.")
    login_chrome.add_argument("--skip-smoke", action="store_true", help="Save cookies without running a Gemini smoke test.")
    login_chrome.add_argument("--no-open", action="store_true", help="Do not open Chrome automatically.")
    login_chrome.add_argument("--timeout", type=int, default=300, help="Seconds to watch Chrome for Gemini cookies.")
    login_chrome.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between cookie checks.")
    login_chrome.add_argument("--wait-for-enter", action="store_true", help="Use the older Enter-confirmation flow.")
    chrome = subparsers.add_parser(
        "import-chrome",
        help="Import Gemini cookies from the user's normal Chrome profile through an explicit local extension.",
    )
    chrome.add_argument("--port", type=int, default=DEFAULT_CHROME_BRIDGE_PORT)
    chrome.add_argument("--timeout", type=int, default=300, help="Seconds to wait for the Chrome extension import.")
    chrome.add_argument("--skip-smoke", action="store_true", help="Save cookies without running a Gemini smoke test.")
    chrome.add_argument("--no-open", action="store_true", help="Do not open Chrome/Finder automatically.")
    subparsers.add_parser("status", help="Show local cookie status without printing secret values.")
    subparsers.add_parser("clear", help="Delete the stored cookie file.")
    return parser.parse_args()


def import_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required for browser login. Install it with: "
            "python3 -m pip install playwright && python3 -m playwright install chromium"
        ) from exc
    return sync_playwright


def command_start(no_block: bool) -> int:
    settings = load_settings()
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    sync_playwright = import_playwright()
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(settings.profile_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(GEMINI_APP_URL, wait_until="domcontentloaded")
        print(f"Opened Gemini login profile: {settings.profile_dir}", file=sys.stderr)
        print("Sign in manually, confirm Gemini loads, then close this helper.", file=sys.stderr)
        if no_block:
            print("Browser closes when this process exits; omit --no-block for normal login.", file=sys.stderr)
            context.close()
            return 0
        try:
            input("Press Enter here after login is complete: ")
        finally:
            context.close()
    return 0


def extract_cookies_from_profile() -> dict[str, str]:
    settings = load_settings()
    sync_playwright = import_playwright()
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(settings.profile_dir), headless=True)
        cookies = context.cookies("https://gemini.google.com")
        context.close()
    values = {}
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if name in REQUIRED_COOKIE_NAMES and isinstance(value, str) and value:
            values[name] = value
    return values


def write_cookie_file(
    values: dict[str, str],
    *,
    source: str = "gemini-writing-copilot dedicated Playwright profile",
) -> Path:
    settings = load_settings()
    payload = {
        "cookie": build_cookie_header(values),
        "sapisid": values.get("SAPISID", ""),
        "values": values,
        "source": source,
        "exported_at": int(time.time()),
    }
    return write_private_json(settings.cookie_file, payload)


def standalone_chrome_data_dir() -> Path:
    settings = load_settings()
    return settings.config_file.parent / STANDALONE_CHROME_DIRNAME


def chrome_executable_path() -> Path:
    for candidate in CHROME_EXECUTABLE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise SystemExit("Google Chrome was not found in /Applications.")


def chrome_cookie_db_path(profile_dir: Path) -> Path:
    network_path = profile_dir / "Network" / "Cookies"
    if network_path.exists():
        return network_path
    return profile_dir / "Cookies"


def load_chrome_profile_names(chrome_data_dir: Path) -> dict[str, str]:
    local_state = chrome_data_dir / "Local State"
    try:
        payload = json.loads(local_state.read_text(encoding="utf-8"))
        info_cache = payload.get("profile", {}).get("info_cache", {})
        if isinstance(info_cache, dict):
            return {
                str(profile_dir): str(info.get("name") or profile_dir)
                for profile_dir, info in info_cache.items()
                if isinstance(info, dict)
            }
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def discover_chrome_profiles(chrome_data_dir: str | Path = "") -> list[dict[str, object]]:
    root = Path(chrome_data_dir).expanduser() if chrome_data_dir else DEFAULT_CHROME_DATA_DIR
    names = load_chrome_profile_names(root)
    candidates = []
    for child in sorted(root.iterdir()) if root.exists() else []:
        if not child.is_dir():
            continue
        if child.name != "Default" and not child.name.startswith("Profile "):
            continue
        cookie_db = chrome_cookie_db_path(child)
        if cookie_db.exists():
            candidates.append(
                {
                    "dir_name": child.name,
                    "display_name": names.get(child.name, child.name),
                    "path": child,
                    "cookie_db": cookie_db,
                }
            )
    candidates.sort(key=lambda item: (0 if item["dir_name"] == "Default" else 1, str(item["dir_name"])))
    return candidates


def select_chrome_profiles(profile: str, chrome_data_dir: str | Path = "") -> list[dict[str, object]]:
    profiles = discover_chrome_profiles(chrome_data_dir)
    selector = profile.strip().lower()
    if not selector:
        return profiles
    selected = [
        item
        for item in profiles
        if str(item["dir_name"]).lower() == selector or str(item["display_name"]).lower() == selector
    ]
    if not selected:
        raise SystemExit(f"Chrome profile not found: {profile}")
    return selected


def get_chrome_safe_storage_password() -> str:
    """Read Chrome's macOS cookie encryption secret through an explicit Keychain prompt."""

    service_names = ("Chrome Safe Storage", "Chromium Safe Storage")
    errors = []
    for service in service_names:
        try:
            proc = subprocess.run(
                ["security", "find-generic-password", "-w", "-s", service],
                check=False,
                text=True,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc))
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        errors.append((proc.stderr or proc.stdout).strip())
    raise SystemExit(
        "Could not read Chrome Safe Storage from macOS Keychain. "
        "You can still use import-chrome or the dedicated start/finish login flow. "
        + redact_secrets("; ".join(error for error in errors if error))
    )


def decrypt_chrome_cookie_value(encrypted_value: bytes, safe_storage_password: str) -> str:
    if not encrypted_value:
        return ""
    blob = bytes(encrypted_value)
    if blob.startswith((b"v10", b"v11")):
        ciphertext = blob[3:]
    else:
        ciphertext = blob
    key = hashlib.pbkdf2_hmac("sha1", safe_storage_password.encode("utf-8"), b"saltysalt", 1003, 16)
    iv = b" " * 16
    cmd = [
        "openssl",
        "enc",
        "-d",
        "-aes-128-cbc",
        "-K",
        key.hex(),
        "-iv",
        iv.hex(),
        "-nosalt",
    ]
    proc = subprocess.run(cmd, input=ciphertext, capture_output=True, check=False, timeout=10)
    if proc.returncode == 0:
        return proc.stdout.decode("utf-8", errors="replace")

    # OpenSSL 3 can be fussy about padding errors. Keep this as a fallback for
    # Chromium-compatible AES-CBC values and strip PKCS#7 manually.
    proc = subprocess.run(cmd + ["-nopad"], input=ciphertext, capture_output=True, check=False, timeout=10)
    if proc.returncode != 0:
        raise ValueError(redact_secrets(proc.stderr.decode("utf-8", errors="replace") or "cookie decrypt failed"))
    raw = proc.stdout
    if raw:
        pad = raw[-1]
        if 1 <= pad <= 16 and raw.endswith(bytes([pad]) * pad):
            raw = raw[:-pad]
    return raw.decode("utf-8", errors="replace")


def cookie_applies_to_gemini(host_key: str) -> bool:
    host = host_key.strip().lstrip(".").lower()
    return host == GEMINI_COOKIE_TARGET_HOST or GEMINI_COOKIE_TARGET_HOST.endswith("." + host)


def copy_cookie_db(cookie_db: Path, temp_dir: Path) -> Path:
    target = temp_dir / "Cookies"
    shutil.copy2(cookie_db, target)
    for suffix in ("-wal", "-shm"):
        sidecar = cookie_db.with_name(cookie_db.name + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, temp_dir / ("Cookies" + suffix))
    return target


def read_chrome_cookie_values(profile_dir: Path, safe_storage_password: str | None = None) -> dict[str, str]:
    cookie_db = chrome_cookie_db_path(profile_dir)
    if not cookie_db.exists():
        raise FileNotFoundError(cookie_db)
    with tempfile.TemporaryDirectory() as tmp:
        copied_db = copy_cookie_db(cookie_db, Path(tmp))
        connection = sqlite3.connect(str(copied_db))
        try:
            placeholders = ",".join("?" for _ in REQUIRED_COOKIE_NAMES)
            rows = connection.execute(
                f"""
                SELECT host_key, name, value, encrypted_value
                FROM cookies
                WHERE name IN ({placeholders})
                """,
                tuple(REQUIRED_COOKIE_NAMES),
            ).fetchall()
        finally:
            connection.close()

    values: dict[str, str] = {}
    specificity: dict[str, int] = {}
    for host_key, name, value, encrypted_value in rows:
        if not cookie_applies_to_gemini(str(host_key)):
            continue
        cookie_value = str(value or "")
        if not cookie_value:
            if safe_storage_password is None:
                safe_storage_password = get_chrome_safe_storage_password()
            cookie_value = decrypt_chrome_cookie_value(encrypted_value or b"", safe_storage_password)
        if not cookie_value:
            continue
        score = len(str(host_key).lstrip("."))
        if name not in values or score >= specificity.get(name, 0):
            values[str(name)] = cookie_value
            specificity[str(name)] = score
    return values


def command_import_chrome_profile(
    *,
    profile: str,
    chrome_data_dir: str,
    list_profiles: bool,
    skip_smoke: bool,
) -> int:
    profiles = select_chrome_profiles(profile, chrome_data_dir)
    if list_profiles:
        if not profiles:
            print("No Chrome profiles with a Cookies database were found.")
            return 1
        for item in profiles:
            print(f"{item['dir_name']}\t{item['display_name']}\t{item['path']}")
        return 0
    if not profiles:
        print("No Chrome profiles with a Cookies database were found.", file=sys.stderr)
        return 1

    safe_storage_password: str | None = None
    best_missing: tuple[str, list[str]] | None = None
    for item in profiles:
        try:
            values = read_chrome_cookie_values(Path(item["path"]), safe_storage_password)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            print(redact_secrets(f"Skipping Chrome profile {item['dir_name']}: {exc}"), file=sys.stderr)
            continue
        missing = missing_required_cookies(values)
        if not missing:
            return save_chrome_import(values, item, skip_smoke=skip_smoke)
        best_missing = (str(item["dir_name"]), missing)
    if best_missing:
        print(
            f"Chrome profile {best_missing[0]} is missing Gemini cookies: " + ", ".join(best_missing[1]),
            file=sys.stderr,
        )
    print("Open https://gemini.google.com/app in Chrome, confirm you are signed in, then try again.", file=sys.stderr)
    return 1


def save_chrome_import(values: dict[str, str], item: dict[str, object], *, skip_smoke: bool) -> int:
    cookie_path = write_cookie_file(
        values,
        source=f"Chrome profile import: {item['dir_name']} ({item['display_name']})",
    )
    print(f"Imported Gemini cookies from Chrome profile: {item['dir_name']} ({item['display_name']})", file=sys.stderr)
    print(f"Saved Gemini cookie bundle: {cookie_path}", file=sys.stderr)
    if skip_smoke:
        return 0
    try:
        run_smoke_test()
    except GeminiWebError as exc:
        print(redact_secrets(f"Cookie saved, but smoke test failed: {exc}"), file=sys.stderr)
        return 2
    print("Smoke test passed.", file=sys.stderr)
    return 0


def open_main_chrome_login(profile: str = "") -> None:
    """Open Gemini in the user's normal Chrome browser."""

    try:
        cmd = ["open", "-a", "Google Chrome", GEMINI_APP_URL]
        subprocess.run(cmd, check=False)
        if profile:
            print(
                "Chrome is open. If Chrome asks which profile to use, choose "
                f"{profile!r}; otherwise use the profile that is already signed in.",
                file=sys.stderr,
            )
    except OSError:
        webbrowser.open(GEMINI_APP_URL)


def command_login_chrome(
    *,
    profile: str,
    chrome_data_dir: str,
    skip_smoke: bool,
    no_open: bool,
    timeout: int,
    poll_interval: float,
    wait_for_enter: bool,
) -> int:
    """Open Chrome for login, then import cookies from the selected profile."""

    profiles = select_chrome_profiles(profile, chrome_data_dir)
    if not profiles:
        print("No Chrome profiles with a Cookies database were found.", file=sys.stderr)
        return 1
    if not no_open:
        open_main_chrome_login(profile or str(profiles[0]["display_name"]))
    print("This reads only Gemini-applicable cookies from the local Chrome profile you explicitly choose.", file=sys.stderr)
    if wait_for_enter:
        print("Confirm Gemini is signed in in Chrome, then press Enter here to import the login.", file=sys.stderr)
        try:
            input("Press Enter after Gemini is signed in: ")
        except EOFError:
            print("No confirmation received; aborting import.", file=sys.stderr)
            return 1
        return command_import_chrome_profile(
            profile=profile,
            chrome_data_dir=chrome_data_dir,
            list_profiles=False,
            skip_smoke=skip_smoke,
        )

    print(f"Watching Chrome for Gemini login cookies for up to {timeout} seconds.", file=sys.stderr)
    print("Just finish the Gemini login in Chrome; import will continue automatically.", file=sys.stderr)
    deadline = time.time() + max(1, timeout)
    best_missing: tuple[str, list[str]] | None = None
    safe_storage_password: str | None = None
    while time.time() < deadline:
        for item in profiles:
            try:
                values = read_chrome_cookie_values(Path(item["path"]), safe_storage_password)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                print(redact_secrets(f"Skipping Chrome profile {item['dir_name']}: {exc}"), file=sys.stderr)
                continue
            missing = missing_required_cookies(values)
            if not missing:
                return save_chrome_import(values, item, skip_smoke=skip_smoke)
            best_missing = (str(item["dir_name"]), missing)
        time.sleep(max(0.5, poll_interval))

    if best_missing:
        print(
            f"Timed out waiting for Gemini cookies in Chrome profile {best_missing[0]}: "
            + ", ".join(best_missing[1]),
            file=sys.stderr,
        )
    else:
        print("Timed out waiting for Gemini cookies in Chrome.", file=sys.stderr)
    return 1


def launch_standalone_chrome_login(data_dir: Path) -> subprocess.Popen:
    data_dir.mkdir(parents=True, exist_ok=True)
    chrome = chrome_executable_path()
    return subprocess.Popen(
        [
            str(chrome),
            f"--user-data-dir={data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=ChromeWhatsNewUI",
            f"--app={GEMINI_APP_URL}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_standalone_chrome(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def command_login_standalone(
    *,
    timeout: int,
    poll_interval: float,
    skip_smoke: bool,
    keep_window: bool,
) -> int:
    """Open an isolated Chrome app window, wait for Google login, then import cookies."""

    data_dir = standalone_chrome_data_dir()
    process = launch_standalone_chrome_login(data_dir)
    print("Opened an independent Google login window for Gemini.", file=sys.stderr)
    print("Finish signing in there; the plugin will import that isolated session automatically.", file=sys.stderr)
    deadline = time.time() + max(1, timeout)
    best_missing: tuple[str, list[str]] | None = None
    try:
        while time.time() < deadline:
            profiles = discover_chrome_profiles(data_dir)
            for item in profiles:
                try:
                    values = read_chrome_cookie_values(Path(item["path"]))
                except SystemExit:
                    raise
                except Exception:
                    continue
                missing = missing_required_cookies(values)
                if not missing:
                    result = save_chrome_import(
                        values,
                        {
                            "dir_name": item["dir_name"],
                            "display_name": "Standalone Google Login",
                        },
                        skip_smoke=skip_smoke,
                    )
                    if not keep_window:
                        stop_standalone_chrome(process)
                    return result
                best_missing = (str(item["dir_name"]), missing)
            time.sleep(max(0.5, poll_interval))
    finally:
        if not keep_window and best_missing is None and process.poll() is not None:
            pass

    if not keep_window:
        stop_standalone_chrome(process)
    if best_missing:
        print(
            "Timed out waiting for standalone Gemini login cookies: " + ", ".join(best_missing[1]),
            file=sys.stderr,
        )
    else:
        print("Timed out waiting for the standalone Gemini login profile.", file=sys.stderr)
    return 1


def chrome_bridge_dir() -> Path:
    settings = load_settings()
    return settings.config_file.parent / CHROME_BRIDGE_DIRNAME


def write_chrome_bridge_extension(*, port: int) -> Path:
    """Create a local Chrome extension that exports only Gemini cookies."""

    extension_dir = chrome_bridge_dir()
    extension_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": 3,
        "name": "Gemini Writing Copilot Cookie Bridge",
        "version": "0.1.0",
        "description": "Explicitly imports gemini.google.com cookies into the local Gemini Writing Copilot plugin.",
        "permissions": ["cookies"],
        "host_permissions": [
            "https://gemini.google.com/*",
            f"http://127.0.0.1:{port}/*",
        ],
        "action": {
            "default_title": "Import Gemini cookies",
            "default_popup": "popup.html",
        },
    }
    (extension_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (extension_dir / "popup.html").write_text(
        """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { width: 310px; margin: 0; padding: 14px; font: 13px -apple-system, BlinkMacSystemFont, sans-serif; color: #202124; }
    button { width: 100%; border: 0; border-radius: 8px; padding: 10px 12px; color: white; background: #1a73e8; font-weight: 600; cursor: pointer; }
    button:disabled { background: #9aa0a6; cursor: default; }
    #status { margin-top: 10px; line-height: 1.4; white-space: pre-wrap; }
  </style>
</head>
<body>
  <button id="import">Import Gemini Login</button>
  <div id="status">Open gemini.google.com in this Chrome profile and sign in first.</div>
  <script src="popup.js"></script>
</body>
</html>
""",
        encoding="utf-8",
    )
    popup_js = f"""const REQUIRED = {json.dumps(list(REQUIRED_COOKIE_NAMES))};
const BRIDGE_URL = "http://127.0.0.1:{port}/import";

const button = document.getElementById("import");
const statusEl = document.getElementById("status");

function setStatus(text) {{
  statusEl.textContent = text;
}}

button.addEventListener("click", async () => {{
  button.disabled = true;
  try {{
    const cookies = await chrome.cookies.getAll({{ domain: "gemini.google.com" }});
    const values = {{}};
    for (const cookie of cookies) {{
      if (REQUIRED.includes(cookie.name) && cookie.value) {{
        values[cookie.name] = cookie.value;
      }}
    }}
    const missing = REQUIRED.filter((name) => !values[name]);
    if (missing.length) {{
      setStatus("Missing Gemini cookies: " + missing.join(", ") + "\\nOpen https://gemini.google.com/app and sign in, then try again.");
      button.disabled = false;
      return;
    }}
    const response = await fetch(BRIDGE_URL, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ values }})
    }});
    if (!response.ok) {{
      throw new Error(await response.text());
    }}
    setStatus("Imported. You can return to Codex.");
  }} catch (error) {{
    setStatus("Import failed: " + error.message);
    button.disabled = false;
  }}
}});
"""
    (extension_dir / "popup.js").write_text(popup_js, encoding="utf-8")
    (extension_dir / "README.txt").write_text(
        "Load this directory as an unpacked Chrome extension, then click its toolbar button while signed into gemini.google.com.\n",
        encoding="utf-8",
    )
    return extension_dir


class _ChromeImportHandler(BaseHTTPRequestHandler):
    server_version = "GeminiWritingChromeBridge/0.1"

    def log_message(self, fmt, *args):
        return

    def _send(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, "")

    def do_POST(self):
        if self.path != "/import":
            self._send(404, "not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            values = payload.get("values") if isinstance(payload, dict) else None
            if not isinstance(values, dict):
                raise ValueError("payload.values must be an object")
            clean_values = {
                str(name): str(value)
                for name, value in values.items()
                if name in REQUIRED_COOKIE_NAMES and isinstance(value, str) and value
            }
            missing = missing_required_cookies(clean_values)
            if missing:
                raise ValueError("missing cookies: " + ", ".join(missing))
            self.server.imported_values = clean_values
            self._send(200, "ok")
        except Exception as exc:  # noqa: BLE001
            self._send(400, redact_secrets(exc))


def open_chrome_bridge_targets(extension_dir: Path) -> None:
    try:
        subprocess.run(["open", "-a", "Google Chrome", GEMINI_APP_URL], check=False)
        subprocess.run(["open", "-a", "Google Chrome", "chrome://extensions/"], check=False)
        subprocess.run(["open", str(extension_dir)], check=False)
    except OSError:
        webbrowser.open(GEMINI_APP_URL)


def command_import_chrome(*, port: int, timeout: int, skip_smoke: bool, no_open: bool) -> int:
    extension_dir = write_chrome_bridge_extension(port=port)
    server = HTTPServer(("127.0.0.1", port), _ChromeImportHandler)
    server.timeout = 0.5
    server.imported_values = None

    print("Chrome import bridge is ready.", file=sys.stderr)
    print(f"Extension folder: {extension_dir}", file=sys.stderr)
    print("In Chrome, load that folder as an unpacked extension, sign into Gemini, then click Import Gemini Login.", file=sys.stderr)
    print("This bridge accepts only gemini.google.com cookie names and writes them locally with 0600 permissions.", file=sys.stderr)
    if not no_open:
        open_chrome_bridge_targets(extension_dir)

    deadline = time.time() + timeout
    try:
        while time.time() < deadline and not server.imported_values:
            server.handle_request()
    finally:
        server.server_close()

    if not server.imported_values:
        print("Timed out waiting for Chrome extension import.", file=sys.stderr)
        return 1

    cookie_path = write_cookie_file(server.imported_values)
    print(f"Saved Gemini cookie bundle: {cookie_path}", file=sys.stderr)
    if skip_smoke:
        return 0
    try:
        run_smoke_test()
    except GeminiWebError as exc:
        print(redact_secrets(f"Cookie saved, but smoke test failed: {exc}"), file=sys.stderr)
        return 2
    print("Smoke test passed.", file=sys.stderr)
    return 0


def run_smoke_test() -> None:
    settings = load_settings()
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


def command_finish(skip_smoke: bool) -> int:
    values = extract_cookies_from_profile()
    missing = missing_required_cookies(values)
    if missing:
        print(
            "Could not find required Gemini cookies in the dedicated profile: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        print("Run scripts/gemini_login.py start, sign in manually, then try finish again.", file=sys.stderr)
        return 1

    cookie_path = write_cookie_file(values)
    print(f"Saved Gemini cookie bundle: {cookie_path}", file=sys.stderr)
    if skip_smoke:
        return 0
    try:
        run_smoke_test()
    except GeminiWebError as exc:
        print(redact_secrets(f"Cookie saved, but smoke test failed: {exc}"), file=sys.stderr)
        return 2
    print("Smoke test passed.", file=sys.stderr)
    return 0


def command_status() -> int:
    settings = load_settings()
    print(f"Config file: {settings.config_file}")
    print(f"Login profile: {settings.profile_dir}")
    print(f"Cookie file: {settings.cookie_file}")
    if not settings.cookie_file.exists():
        print("Cookie status: missing")
        return 1
    mode = stat.S_IMODE(settings.cookie_file.stat().st_mode)
    print(f"Cookie file mode: {oct(mode)}")
    try:
        cookie_data = load_cookie_file(settings.cookie_file)
    except Exception as exc:  # noqa: BLE001 - status should explain malformed local files.
        print(redact_secrets(f"Cookie status: unreadable ({exc})"))
        return 1
    missing = missing_required_cookies(cookie_data.values)
    if missing:
        print("Cookie status: incomplete")
        print("Missing cookies: " + ", ".join(missing))
        return 1
    if mode != 0o600:
        print("Cookie status: present, but permissions should be 0600")
        return 1
    print("Cookie status: ready")
    return 0


def command_clear() -> int:
    settings = load_settings()
    if settings.cookie_file.exists():
        settings.cookie_file.unlink()
        print(f"Deleted cookie file: {settings.cookie_file}", file=sys.stderr)
    else:
        print("Cookie file already missing.", file=sys.stderr)
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.command == "start":
            return command_start(args.no_block)
        if args.command == "finish":
            return command_finish(args.skip_smoke)
        if args.command == "login-standalone":
            return command_login_standalone(
                timeout=args.timeout,
                poll_interval=args.poll_interval,
                skip_smoke=args.skip_smoke,
                keep_window=args.keep_window,
            )
        if args.command == "import-chrome-profile":
            return command_import_chrome_profile(
                profile=args.profile,
                chrome_data_dir=args.chrome_data_dir,
                list_profiles=args.list_profiles,
                skip_smoke=args.skip_smoke,
            )
        if args.command == "login-chrome":
            return command_login_chrome(
                profile=args.profile,
                chrome_data_dir=args.chrome_data_dir,
                skip_smoke=args.skip_smoke,
                no_open=args.no_open,
                timeout=args.timeout,
                poll_interval=args.poll_interval,
                wait_for_enter=args.wait_for_enter,
            )
        if args.command == "import-chrome":
            return command_import_chrome(
                port=args.port,
                timeout=args.timeout,
                skip_smoke=args.skip_smoke,
                no_open=args.no_open,
            )
        if args.command == "status":
            return command_status()
        if args.command == "clear":
            return command_clear()
        raise SystemExit("unknown command")
    except SystemExit as exc:
        print(redact_secrets(exc), file=sys.stderr)
        return exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:  # noqa: BLE001 - keep CLI errors concise and redacted.
        print(redact_secrets(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
