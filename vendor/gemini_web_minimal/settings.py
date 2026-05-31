"""Shared configuration for plugin scripts."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from .models import DEFAULT_MODEL

APP_NAME = "gemini-writing-copilot"
APP_CONFIG_DIR = Path.home() / ".config" / APP_NAME
DEFAULT_COOKIE_FILE = APP_CONFIG_DIR / "cookie.json"
DEFAULT_CONFIG_FILE = APP_CONFIG_DIR / "config.json"
DEFAULT_PROFILE_DIR = APP_CONFIG_DIR / "browser-profile"
DEFAULT_STYLE_PROFILE_DIR = APP_CONFIG_DIR / "profiles"


@dataclass(frozen=True)
class Settings:
    cookie_file: Path
    provider: str
    agy_bin: str | None
    model: str
    think: int | None
    timeout_sec: int
    retry_attempts: int
    retry_delay_sec: float
    proxy: str | None
    config_file: Path
    profile_dir: Path
    style_profile_dir: Path


def _load_config_file(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _get_int(value: object, default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _get_float(value: object, default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)


def load_settings() -> Settings:
    config_file = Path(os.environ.get("GEMINI_WRITING_CONFIG_FILE", DEFAULT_CONFIG_FILE)).expanduser()
    config = _load_config_file(config_file)

    cookie_file = Path(
        os.environ.get("GEMINI_WRITING_COOKIE_FILE", config.get("cookie_file", DEFAULT_COOKIE_FILE))
    ).expanduser()
    profile_dir = Path(config.get("profile_dir", DEFAULT_PROFILE_DIR)).expanduser()
    style_profile_dir = Path(
        os.environ.get("GEMINI_WRITING_STYLE_PROFILE_DIR", config.get("style_profile_dir", DEFAULT_STYLE_PROFILE_DIR))
    ).expanduser()
    provider = str(os.environ.get("GEMINI_WRITING_PROVIDER", config.get("provider", "antigravity"))).lower()
    if provider not in {"antigravity", "web", "auto"}:
        raise ValueError("GEMINI_WRITING_PROVIDER must be one of: antigravity, web, auto")
    agy_bin_raw = os.environ.get("GEMINI_WRITING_AGY_BIN", config.get("agy_bin", ""))
    agy_bin = str(agy_bin_raw).strip() if agy_bin_raw else None
    model = str(os.environ.get("GEMINI_WRITING_MODEL", config.get("model", DEFAULT_MODEL)))
    think_raw = os.environ.get("GEMINI_WRITING_THINK", config.get("think"))
    think = None if think_raw in (None, "") else int(think_raw)
    timeout = _get_int(os.environ.get("GEMINI_WRITING_TIMEOUT_SEC", config.get("timeout_sec")), 180)
    retry_attempts = _get_int(config.get("retry_attempts"), 3)
    retry_delay = _get_float(config.get("retry_delay_sec"), 2.0)
    proxy = (
        os.environ.get("GEMINI_WRITING_PROXY")
        or config.get("proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
    )
    return Settings(
        cookie_file=cookie_file,
        provider=provider,
        agy_bin=agy_bin,
        model=model,
        think=think,
        timeout_sec=timeout,
        retry_attempts=retry_attempts,
        retry_delay_sec=retry_delay,
        proxy=str(proxy) if proxy else None,
        config_file=config_file,
        profile_dir=profile_dir,
        style_profile_dir=style_profile_dir,
    )
