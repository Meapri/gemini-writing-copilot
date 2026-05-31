"""Minimal Gemini Web client used by the Gemini Writing Copilot plugin."""

from .antigravity_cli import (
    antigravity_settings_file,
    antigravity_token_file,
    clean_antigravity_output,
    find_agy,
    run_antigravity_print,
    selected_antigravity_model,
)
from .client import GeminiWebClient
from .cookies import CookieData, load_cookie_file, make_sapisidhash, parse_cookie_text
from .errors import GeminiWebError
from .models import MODELS, ResolvedModel, resolve_model
from .prompting import build_writing_prompt
from .redaction import redact_secrets
from .secure_io import write_private_json

__all__ = [
    "CookieData",
    "GeminiWebClient",
    "GeminiWebError",
    "MODELS",
    "ResolvedModel",
    "antigravity_settings_file",
    "antigravity_token_file",
    "build_writing_prompt",
    "clean_antigravity_output",
    "find_agy",
    "load_cookie_file",
    "make_sapisidhash",
    "parse_cookie_text",
    "redact_secrets",
    "resolve_model",
    "run_antigravity_print",
    "selected_antigravity_model",
    "write_private_json",
]
