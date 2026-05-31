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
from .errors import GeminiWebError, friendly_error_message
from .models import MODELS, ResolvedModel, resolve_model
from .prompting import build_writing_prompt
from .project_context import collect_project_context
from .quality import clean_candidate_output, review_output
from .redaction import redact_secrets
from .routing import defaults_for_task, infer_task, should_use_writing_skill
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
    "clean_candidate_output",
    "collect_project_context",
    "defaults_for_task",
    "find_agy",
    "friendly_error_message",
    "infer_task",
    "load_cookie_file",
    "make_sapisidhash",
    "parse_cookie_text",
    "redact_secrets",
    "review_output",
    "resolve_model",
    "run_antigravity_print",
    "selected_antigravity_model",
    "should_use_writing_skill",
    "write_private_json",
]
