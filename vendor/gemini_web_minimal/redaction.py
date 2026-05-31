"""Secret redaction helpers for CLI stderr output."""

from __future__ import annotations

import re

COOKIE_VALUE_RE = re.compile(
    r"(?i)\b(SID|HSID|SSID|APISID|SAPISID|__Secure-1PSID)=([^;\s]+)"
)
AUTH_RE = re.compile(r"(?i)(Authorization:\s*)(Bearer|SAPISIDHASH)\s+([A-Za-z0-9_.:-]+)")


def redact_secrets(text: object) -> str:
    value = str(text)
    value = COOKIE_VALUE_RE.sub(lambda m: f"{m.group(1)}=<redacted>", value)
    value = AUTH_RE.sub(lambda m: f"{m.group(1)}{m.group(2)} <redacted>", value)
    return value
