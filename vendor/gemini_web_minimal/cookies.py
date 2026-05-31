"""Cookie parsing and SAPISIDHASH helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time

REQUIRED_COOKIE_NAMES = (
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-1PSID",
)


@dataclass(frozen=True)
class CookieData:
    cookie: str
    sapisid: str | None
    values: dict[str, str]


def parse_cookie_header(cookie_header: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in cookie_header.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            values[key] = value
    return values


def build_cookie_header(values: dict[str, str]) -> str:
    return "; ".join(f"{name}={values[name]}" for name in values if values[name])


def parse_cookie_text(text: str) -> CookieData:
    """Parse JSON or raw ``Cookie:`` style text into a cookie bundle."""

    stripped = text.strip()
    if not stripped:
        return CookieData(cookie="", sapisid=None, values={})

    if stripped.startswith("{"):
        data = json.loads(stripped)
        if not isinstance(data, dict):
            raise ValueError("cookie JSON must be an object")
        cookie = str(data.get("cookie", "")).strip()
        values = parse_cookie_header(cookie)
        raw_values = data.get("values")
        if isinstance(raw_values, dict):
            for key, value in raw_values.items():
                if isinstance(key, str) and isinstance(value, str):
                    values[key] = value
            cookie = build_cookie_header(values)
        sapisid = str(data.get("sapisid", "") or values.get("SAPISID", "")).strip()
        return CookieData(cookie=cookie, sapisid=sapisid or None, values=values)

    if stripped.lower().startswith("cookie:"):
        stripped = stripped.split(":", 1)[1].strip()
    values = parse_cookie_header(stripped)
    return CookieData(cookie=build_cookie_header(values), sapisid=values.get("SAPISID"), values=values)


def load_cookie_file(path: str | Path) -> CookieData:
    return parse_cookie_text(Path(path).expanduser().read_text(encoding="utf-8"))


def make_sapisidhash(sapisid: str, *, timestamp: int | None = None) -> str:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    digest = hashlib.sha1(f"{ts} {sapisid} https://gemini.google.com".encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{digest}"


def missing_required_cookies(values: dict[str, str]) -> list[str]:
    return [name for name in REQUIRED_COOKIE_NAMES if not values.get(name)]
