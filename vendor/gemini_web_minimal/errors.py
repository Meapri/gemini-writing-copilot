"""Error types for the minimal Gemini Web client."""

from __future__ import annotations


class GeminiWebError(RuntimeError):
    """Raised when Gemini Web cannot produce a usable text response."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status
