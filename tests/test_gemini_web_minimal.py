from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import urllib.parse
from unittest import mock
import importlib.util
import sqlite3

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "vendor"))

from gemini_web_minimal import (
    GeminiWebError,
    build_writing_prompt,
    make_sapisidhash,
    parse_cookie_text,
    redact_secrets,
    resolve_model,
)
from gemini_web_minimal import antigravity_cli
from gemini_web_minimal.protocol import build_payload, extract_response_text
from gemini_web_minimal.secure_io import write_private_json


def load_script_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, PLUGIN_ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GeminiWebMinimalTests(unittest.TestCase):
    def test_build_payload_sets_model_and_thinking_fields(self):
        body = build_payload("Write better prose", model_id=2, think_mode=0)
        params = urllib.parse.parse_qs(body)
        outer = json.loads(params["f.req"][0])
        inner = json.loads(outer[1])

        self.assertEqual(inner[0][0], "Write better prose")
        self.assertEqual(inner[17], [[0]])
        self.assertEqual(inner[79], 2)

    def test_resolve_model_accepts_antigravity_alias_and_provider_prefix(self):
        resolved = resolve_model("google/gemini-3.1-pro-high")

        self.assertEqual(resolved.name, "gemini-3.1-pro")
        self.assertEqual(resolved.think, 0)
        self.assertEqual(resolved.alias_used, "gemini-3.1-pro-high")

    def test_resolve_model_suffix_overrides_alias_thinking(self):
        resolved = resolve_model("gemini-3.5-flash-low@think=2")

        self.assertEqual(resolved.name, "gemini-3.5-flash")
        self.assertEqual(resolved.think, 2)

    def test_resolve_model_unknown_falls_back_to_pro_high_alias(self):
        resolved = resolve_model("unknown-model")

        self.assertEqual(resolved.name, "gemini-3.1-pro")
        self.assertEqual(resolved.think, 0)
        self.assertTrue(resolved.fallback_used)

    def test_parse_cookie_json_and_sapisidhash(self):
        parsed = parse_cookie_text(
            json.dumps(
                {
                    "cookie": "SID=sid; SAPISID=sapi",
                    "values": {"HSID": "hsid"},
                }
            )
        )
        expected_hash = hashlib.sha1(b"123 sapi https://gemini.google.com").hexdigest()

        self.assertEqual(parsed.values["SID"], "sid")
        self.assertEqual(parsed.values["HSID"], "hsid")
        self.assertEqual(parsed.sapisid, "sapi")
        self.assertEqual(make_sapisidhash("sapi", timestamp=123), f"SAPISIDHASH 123_{expected_hash}")

    def test_extract_response_text_uses_longest_text(self):
        short_inner = [None] * 5
        short_inner[4] = [[None, ["short" + "x" * 210]]]
        long_text = "final prose " + "y" * 230
        long_inner = [None] * 5
        long_inner[4] = [[None, [long_text]]]
        raw = "\n".join(
            [
                json.dumps([["wrb.fr", None, json.dumps(short_inner)]]),
                json.dumps([["wrb.fr", None, json.dumps(long_inner)]]),
            ]
        )

        self.assertEqual(extract_response_text(raw), long_text)

    def test_redact_secrets(self):
        text = "Cookie: SID=abc; SAPISID=def\nAuthorization: Bearer token"

        redacted = redact_secrets(text)

        self.assertNotIn("abc", redacted)
        self.assertNotIn("def", redacted)
        self.assertNotIn("token", redacted)

    def test_write_private_json_uses_0600_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cookie.json"

            write_private_json(path, {"secret": "value"})

            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"secret": "value"})

    def test_build_writing_prompt_uses_composition_brief(self):
        prompt = build_writing_prompt(
            task="polish",
            instruction="Make it warmer without adding facts.",
            source_text="rough text",
            tone="calm",
            audience="maintainers",
            length="two short paragraphs",
            style_guide="Plain language. No hype.",
            variants=3,
            output_mode="edit-with-notes",
            preserve_voice="strong",
            structure_mode="preserve",
            rewrite_strength="light",
        )

        self.assertIn("Composition principles:", prompt)
        self.assertIn("For Korean writing, prefer natural modern Korean", prompt)
        self.assertIn("Correct minor errors without changing the core sentence structures.", prompt)
        self.assertIn("Return the revised text followed by concise notes explaining key changes.", prompt)
        self.assertIn("Strictly maintain the original voice", prompt)
        self.assertIn("Maintain existing paragraph boundaries", prompt)
        self.assertIn("Correct grammar and spelling while preserving sentence structure.", prompt)
        self.assertIn("Requested variants:\n3", prompt)
        self.assertIn("Style guide:\nPlain language. No hype.", prompt)
        self.assertIn("Length:\ntwo short paragraphs", prompt)
        self.assertIn("Source text:\nrough text", prompt)

    def test_build_writing_prompt_keeps_translate_guidance(self):
        prompt = build_writing_prompt(
            task="translate",
            source_text="안녕하세요",
            target_language="English",
        )

        self.assertIn("Convert the source text into the target language accurately.", prompt)
        self.assertIn("Target language:\nEnglish", prompt)

    def test_build_writing_prompt_supports_specialized_task_and_output_mode(self):
        prompt = build_writing_prompt(
            task="pr-description",
            context="Changed the login provider.",
            output_mode="diff-summary",
            rewrite_strength="heavy",
        )

        self.assertIn("Task: pr-description", prompt)
        self.assertIn("Summarize the changes made in the pull request clearly.", prompt)
        self.assertIn("Output a concise list of modifications made", prompt)
        self.assertIn("Completely restructure paragraphs", prompt)

    def test_writer_loads_builtin_and_user_style_profiles(self):
        writer = load_script_module("_test_gemini_write_profiles", "gemini_write.py")
        builtin = writer.load_style_profile("github-release", user_profile_dir=Path("/tmp/missing-profiles"))
        self.assertIn("release notes", builtin)

        with tempfile.TemporaryDirectory() as tmp:
            profile_dir = Path(tmp)
            (profile_dir / "custom.md").write_text("Custom voice profile", encoding="utf-8")
            args = SimpleNamespace(profile=["custom"], profile_dir=str(profile_dir), style_guide="Extra rule")
            settings = SimpleNamespace(style_profile_dir=Path("/tmp/default-profiles"))

            combined = writer.build_style_guide(args, settings)

        self.assertIn("Profile custom:\nCustom voice profile", combined)
        self.assertIn("Extra rule", combined)

    def test_writer_rejects_unsafe_profile_names(self):
        writer = load_script_module("_test_gemini_write_profile_safety", "gemini_write.py")

        with self.assertRaises(ValueError):
            writer.load_style_profile("../secret", user_profile_dir=Path("/tmp/missing-profiles"))

    def test_gemini_write_mock_outputs_body_only(self):
        env = os.environ.copy()
        env["GEMINI_WRITING_MOCK_RESPONSE"] = "Polished result"
        proc = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "gemini_write.py"),
                "--task",
                "polish",
                "--source-text",
                "rough text",
            ],
            check=False,
            text=True,
            capture_output=True,
            env=env,
        )

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "Polished result\n")

    def test_antigravity_cli_cleans_output_and_passes_print_timeout(self):
        completed = SimpleNamespace(returncode=0, stdout="\x1b[32mAnswer\r\n", stderr="")
        with mock.patch.object(antigravity_cli, "find_agy", return_value="/usr/local/bin/agy"):
            with mock.patch.object(antigravity_cli.subprocess, "run", return_value=completed) as run_mock:
                result = antigravity_cli.run_antigravity_print("Prompt", timeout_sec=12)

        self.assertEqual(result, "Answer")
        command = run_mock.call_args.args[0]
        self.assertEqual(command[:3], ["/usr/local/bin/agy", "--print", "Prompt"])
        self.assertEqual(command[-2:], ["--print-timeout", "12s"])

    def test_antigravity_cli_failure_redacts_secrets(self):
        completed = SimpleNamespace(returncode=1, stdout="", stderr="Authorization: Bearer secret-token")
        with mock.patch.object(antigravity_cli, "find_agy", return_value="/usr/local/bin/agy"):
            with mock.patch.object(antigravity_cli.subprocess, "run", return_value=completed):
                with self.assertRaises(GeminiWebError) as raised:
                    antigravity_cli.run_antigravity_print("Prompt", timeout_sec=12)

        self.assertNotIn("secret-token", str(raised.exception))

    def test_writer_auto_provider_prefers_antigravity_when_agy_exists(self):
        writer = load_script_module("_test_gemini_write_provider_auto", "gemini_write.py")
        args = SimpleNamespace(provider=None)
        settings = SimpleNamespace(provider="auto", agy_bin="")
        with mock.patch.object(writer, "find_agy", return_value="/usr/local/bin/agy"):
            self.assertEqual(writer.resolve_provider(args, settings), "antigravity")

    def test_writer_default_provider_uses_settings(self):
        writer = load_script_module("_test_gemini_write_provider_default", "gemini_write.py")
        args = SimpleNamespace(provider=None)
        settings = SimpleNamespace(provider="antigravity", agy_bin="")

        self.assertEqual(writer.resolve_provider(args, settings), "antigravity")

    def test_gemini_write_rejects_empty_input_before_mock(self):
        env = os.environ.copy()
        env["GEMINI_WRITING_MOCK_RESPONSE"] = "unused"
        proc = subprocess.run(
            [sys.executable, str(PLUGIN_ROOT / "scripts" / "gemini_write.py"), "--task", "polish"],
            check=False,
            text=True,
            capture_output=True,
            env=env,
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Nothing to send to Gemini", proc.stderr)

    def test_chrome_bridge_extension_is_domain_scoped(self):
        login = load_script_module("_test_gemini_login", "gemini_login.py")
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            with mock.patch.dict(os.environ, {"GEMINI_WRITING_CONFIG_FILE": str(config_path)}):
                extension_dir = login.write_chrome_bridge_extension(port=19876)

            manifest = json.loads((extension_dir / "manifest.json").read_text(encoding="utf-8"))
            popup_js = (extension_dir / "popup.js").read_text(encoding="utf-8")

            self.assertEqual(manifest["permissions"], ["cookies"])
            self.assertEqual(
                manifest["host_permissions"],
                ["https://gemini.google.com/*", "http://127.0.0.1:19876/*"],
            )
            for cookie_name in ("SID", "SAPISID", "__Secure-1PSID"):
                self.assertIn(cookie_name, popup_js)
            self.assertIn("http://127.0.0.1:19876/import", popup_js)

    def test_direct_chrome_profile_import_reads_only_gemini_applicable_cookies(self):
        login = load_script_module("_test_gemini_login_direct", "gemini_login.py")
        with tempfile.TemporaryDirectory() as tmp:
            profile_dir = Path(tmp) / "Default"
            network_dir = profile_dir / "Network"
            network_dir.mkdir(parents=True)
            cookie_db = network_dir / "Cookies"
            connection = sqlite3.connect(cookie_db)
            try:
                connection.execute(
                    """
                    CREATE TABLE cookies (
                      host_key TEXT,
                      name TEXT,
                      value TEXT,
                      encrypted_value BLOB
                    )
                    """
                )
                for name in login.REQUIRED_COOKIE_NAMES:
                    connection.execute(
                        "INSERT INTO cookies VALUES (?, ?, ?, ?)",
                        (".google.com", name, f"value-{name}", b""),
                    )
                connection.execute(
                    "INSERT INTO cookies VALUES (?, ?, ?, ?)",
                    ("accounts.google.com", "SID", "wrong-scope", b""),
                )
                connection.commit()
            finally:
                connection.close()

            values = login.read_chrome_cookie_values(profile_dir)

        self.assertEqual(values["SID"], "value-SID")
        self.assertEqual(values["SAPISID"], "value-SAPISID")
        self.assertNotIn("wrong-scope", values.values())

    def test_discover_chrome_profiles_uses_local_state_display_name(self):
        login = load_script_module("_test_gemini_login_profiles", "gemini_login.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_dir = root / "Profile 1" / "Network"
            profile_dir.mkdir(parents=True)
            (profile_dir / "Cookies").write_bytes(b"")
            (root / "Local State").write_text(
                json.dumps({"profile": {"info_cache": {"Profile 1": {"name": "Writing"}}}}),
                encoding="utf-8",
            )

            profiles = login.discover_chrome_profiles(root)

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["dir_name"], "Profile 1")
        self.assertEqual(profiles[0]["display_name"], "Writing")

    def test_login_chrome_can_use_enter_confirmation_flow(self):
        login = load_script_module("_test_gemini_login_chrome", "gemini_login.py")
        fake_profile = {"dir_name": "Default", "display_name": "Main", "path": Path("/tmp/default")}
        with mock.patch.object(login, "select_chrome_profiles", return_value=[fake_profile]) as select_mock:
            with mock.patch.object(login, "open_main_chrome_login") as open_mock:
                with mock.patch.object(login, "command_import_chrome_profile", return_value=0) as import_mock:
                    with mock.patch("builtins.input", return_value=""):
                        code = login.command_login_chrome(
                            profile="Default",
                            chrome_data_dir="",
                            skip_smoke=True,
                            no_open=False,
                            timeout=1,
                            poll_interval=0.5,
                            wait_for_enter=True,
                        )

        self.assertEqual(code, 0)
        select_mock.assert_called_once_with("Default", "")
        open_mock.assert_called_once_with("Default")
        import_mock.assert_called_once_with(
            profile="Default",
            chrome_data_dir="",
            list_profiles=False,
            skip_smoke=True,
        )

    def test_login_chrome_default_watches_profile_without_enter(self):
        login = load_script_module("_test_gemini_login_watch", "gemini_login.py")
        fake_profile = {"dir_name": "Default", "display_name": "Main", "path": Path("/tmp/default")}
        values = {name: f"value-{name}" for name in login.REQUIRED_COOKIE_NAMES}
        with mock.patch.object(login, "select_chrome_profiles", return_value=[fake_profile]):
            with mock.patch.object(login, "open_main_chrome_login") as open_mock:
                with mock.patch.object(login, "read_chrome_cookie_values", return_value=values) as read_mock:
                    with mock.patch.object(login, "save_chrome_import", return_value=0) as save_mock:
                        code = login.command_login_chrome(
                            profile="",
                            chrome_data_dir="",
                            skip_smoke=True,
                            no_open=False,
                            timeout=1,
                            poll_interval=0.5,
                            wait_for_enter=False,
                        )

        self.assertEqual(code, 0)
        open_mock.assert_called_once_with("Main")
        read_mock.assert_called_once_with(Path("/tmp/default"), None)
        save_mock.assert_called_once_with(values, fake_profile, skip_smoke=True)

    def test_login_standalone_imports_isolated_profile_and_closes_window(self):
        login = load_script_module("_test_gemini_login_standalone", "gemini_login.py")
        fake_process = mock.Mock()
        fake_profile = {"dir_name": "Default", "display_name": "Default", "path": Path("/tmp/standalone/Default")}
        values = {name: f"value-{name}" for name in login.REQUIRED_COOKIE_NAMES}
        with mock.patch.object(login, "standalone_chrome_data_dir", return_value=Path("/tmp/standalone")):
            with mock.patch.object(login, "launch_standalone_chrome_login", return_value=fake_process) as launch_mock:
                with mock.patch.object(login, "discover_chrome_profiles", return_value=[fake_profile]) as discover_mock:
                    with mock.patch.object(login, "read_chrome_cookie_values", return_value=values):
                        with mock.patch.object(login, "save_chrome_import", return_value=0) as save_mock:
                            with mock.patch.object(login, "stop_standalone_chrome") as stop_mock:
                                code = login.command_login_standalone(
                                    timeout=1,
                                    poll_interval=0.5,
                                    skip_smoke=True,
                                    keep_window=False,
                                )

        self.assertEqual(code, 0)
        launch_mock.assert_called_once_with(Path("/tmp/standalone"))
        discover_mock.assert_called_once_with(Path("/tmp/standalone"))
        save_mock.assert_called_once()
        stop_mock.assert_called_once_with(fake_process)

    def test_writer_auto_login_defaults_to_standalone(self):
        writer = load_script_module("_test_gemini_write_auto_login", "gemini_write.py")
        args = SimpleNamespace(auto_login=True, auto_login_mode="standalone", login_timeout=7)
        settings = SimpleNamespace(cookie_file=Path("/tmp/missing-cookie.json"))
        completed = SimpleNamespace(returncode=0)
        with mock.patch.object(writer, "load_settings", return_value=settings):
            with mock.patch.object(writer, "cookie_ready", return_value=False):
                with mock.patch.object(writer.subprocess, "run", return_value=completed) as run_mock:
                    writer.ensure_login_if_requested(args)

        command = run_mock.call_args.args[0]
        self.assertIn("login-standalone", command)
        self.assertIn("--timeout", command)
        self.assertIn("7", command)

    def test_writer_auto_login_reuses_ready_cookie_without_launching(self):
        writer = load_script_module("_test_gemini_write_ready_login", "gemini_write.py")
        args = SimpleNamespace(auto_login=True, auto_login_mode="standalone", login_timeout=7)
        settings = SimpleNamespace(cookie_file=Path("/tmp/ready-cookie.json"))
        with mock.patch.object(writer, "load_settings", return_value=settings):
            with mock.patch.object(writer, "cookie_ready", return_value=True):
                with mock.patch.object(writer.subprocess, "run") as run_mock:
                    writer.ensure_login_if_requested(args)

        run_mock.assert_not_called()

    def test_writer_relogs_on_rejected_cookie_and_retries(self):
        writer = load_script_module("_test_gemini_write_relogin", "gemini_write.py")
        args = SimpleNamespace(auto_login=True, auto_login_mode="standalone", login_timeout=7)
        client = mock.Mock()
        client.generate.side_effect = [GeminiWebError("rejected", status=403), "ok"]
        with mock.patch.object(writer, "ensure_login_if_requested") as ensure_mock:
            result = writer.generate_with_optional_relogin(client, "prompt", args)

        self.assertEqual(result, "ok")
        ensure_mock.assert_called_once()
        self.assertTrue(ensure_mock.call_args.kwargs["force"])


if __name__ == "__main__":
    unittest.main()
