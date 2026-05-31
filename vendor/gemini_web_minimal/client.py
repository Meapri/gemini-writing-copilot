"""Small Gemini Web client for one-shot text generation."""

from __future__ import annotations

from dataclasses import dataclass
import ssl
import time
import urllib.error
import urllib.request

from .cookies import CookieData, load_cookie_file, make_sapisidhash
from .errors import GeminiWebError
from .models import DEFAULT_MODEL, resolve_model
from .protocol import DEFAULT_GEMINI_BL, build_payload, build_stream_generate_url, extract_response_text
from .redaction import redact_secrets


@dataclass
class GeminiWebClient:
    cookie_file: str
    model: str = DEFAULT_MODEL
    think: int | None = None
    timeout_sec: int = 180
    retry_attempts: int = 3
    retry_delay_sec: float = 2.0
    proxy: str | None = None
    gemini_bl: str = DEFAULT_GEMINI_BL

    def generate(self, prompt: str) -> str:
        if not prompt.strip():
            raise GeminiWebError("empty prompt")

        resolved = resolve_model(self.model, think_override=self.think)
        cookie_data = load_cookie_file(self.cookie_file)
        if not cookie_data.cookie:
            raise GeminiWebError("Gemini cookie file is empty. Run scripts/gemini_login.py first.")

        body = build_payload(
            prompt,
            model_id=resolved.mode,
            think_mode=resolved.think,
            extra_fields=resolved.extra_fields,
        ).encode("utf-8")
        headers = self._headers(cookie_data)
        ctx = ssl.create_default_context()
        reqid = int(time.time()) % 1000000
        url = build_stream_generate_url(gemini_bl=self.gemini_bl, reqid=reqid)

        last_error: Exception | None = None
        for attempt in range(max(1, self.retry_attempts)):
            try:
                request = urllib.request.Request(url, data=body, headers=headers, method="POST")
                response = self._open(request, ctx)
                raw = response.read().decode("utf-8", errors="replace")
                text = extract_response_text(raw)
                if not text:
                    raise GeminiWebError("Gemini returned an empty response")
                return text
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in {401, 403}:
                    raise GeminiWebError(
                        "Gemini rejected the stored login cookie. Run scripts/gemini_login.py start, then finish.",
                        status=exc.code,
                    ) from exc
                if exc.code == 429:
                    raise GeminiWebError("Gemini rate-limited this account. Try again later.", status=exc.code) from exc
            except Exception as exc:  # noqa: BLE001 - convert all transport errors for CLI users.
                last_error = exc

            if attempt < max(1, self.retry_attempts) - 1:
                time.sleep(self.retry_delay_sec)

        message = redact_secrets(last_error or "unknown upstream error")
        raise GeminiWebError(f"Gemini Web request failed: {message}") from last_error

    def _headers(self, cookie_data: CookieData) -> dict[str, str]:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://gemini.google.com",
            "Referer": "https://gemini.google.com/app",
            "X-Same-Domain": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Cookie": cookie_data.cookie,
        }
        if cookie_data.sapisid:
            headers["Authorization"] = make_sapisidhash(cookie_data.sapisid)
        return headers

    def _open(self, request: urllib.request.Request, ctx: ssl.SSLContext):
        if self.proxy:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}),
                urllib.request.HTTPSHandler(context=ctx),
            )
            return opener.open(request, timeout=self.timeout_sec)
        return urllib.request.urlopen(request, context=ctx, timeout=self.timeout_sec)
