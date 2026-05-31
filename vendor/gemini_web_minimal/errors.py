"""Error types for the minimal Gemini Web client."""

from __future__ import annotations


class GeminiWebError(RuntimeError):
    """Raised when Gemini Web cannot produce a usable text response."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def friendly_error_message(error: object) -> str:
    """Convert provider errors into user-facing repair hints."""

    message = str(error)
    lowered = message.lower()
    if "agy" in lowered and "not found" in lowered:
        return (
            "Antigravity CLI (`agy`) was not found. Open or install Google Antigravity first, "
            "or set GEMINI_WRITING_AGY_BIN to the agy binary path."
        )
    if "timeout" in lowered or "did not finish" in lowered:
        return (
            "Antigravity/Gemini did not finish before the timeout. If a Google login or account "
            "chooser is open, complete it once and retry. You can also increase GEMINI_WRITING_TIMEOUT_SEC."
        )
    if "rate-limited" in lowered or "429" in lowered:
        return "Gemini rate-limited this account. Wait a bit and retry the same writing request."
    if "401" in lowered or "403" in lowered or "rejected the stored login" in lowered:
        return (
            "The stored Gemini login was rejected. For the default Antigravity provider, let the "
            "Antigravity login/account chooser complete once, then retry. For the web fallback, rerun the login helper."
        )
    if "empty response" in lowered:
        return "Gemini returned an empty response. Retry once; if it repeats, run scripts/gemini_doctor.py."
    if "quality gate" in lowered:
        return (
            "Gemini returned text that did not pass the writing quality gate. Add more source/context, "
            "or use --quality-gate warn if you want Codex to review warnings instead of blocking."
        )
    return message
