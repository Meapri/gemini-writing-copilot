"""Gemini Web model mapping adapted from Sophomoresty/gemini-web2api."""

from __future__ import annotations

from dataclasses import dataclass


MODELS = {
    "gemini-3.5-flash": {
        "mode": 1,
        "think": 4,
        "desc": "Fast general-purpose model",
    },
    "gemini-3.5-flash-thinking": {
        "mode": 2,
        "think": 0,
        "desc": "Deep thinking mode, longest output",
    },
    "gemini-3.1-pro": {
        "mode": 3,
        "think": 4,
        "desc": "Pro model routing when the account cookie has access",
    },
    "gemini-3.1-pro-enhanced": {
        "mode": 3,
        "think": 4,
        "extra": {31: 2, 80: 3},
        "desc": "Pro model with enhanced output fields",
    },
    "gemini-auto": {
        "mode": 4,
        "think": 4,
        "desc": "Gemini web auto model selection",
    },
    "gemini-3.5-flash-thinking-lite": {
        "mode": 5,
        "think": 0,
        "desc": "Dynamic thinking with adaptive depth",
    },
    "gemini-flash-lite": {
        "mode": 6,
        "think": 4,
        "desc": "Lightweight fast model",
    },
}

DEFAULT_MODEL = "gemini-3.1-pro-high"


@dataclass(frozen=True)
class ResolvedModel:
    name: str
    mode: int
    think: int
    extra_fields: dict[int, object] | None = None
    fallback_used: bool = False
    alias_used: str | None = None


ANTIGRAVITY_MODEL_ALIASES: dict[str, tuple[str, int]] = {
    "gemini-3.5-flash-high": ("gemini-3.5-flash-thinking", 0),
    "gemini-3.5-flash-medium": ("gemini-3.5-flash-thinking", 2),
    "gemini-3.5-flash-low": ("gemini-3.5-flash", 4),
    "gemini-3-flash-high": ("gemini-3.5-flash-thinking", 0),
    "gemini-3-flash-medium": ("gemini-3.5-flash-thinking", 2),
    "gemini-3-flash-low": ("gemini-3.5-flash", 4),
    "gemini-3-flash": ("gemini-3.5-flash", 4),
    "gemini-3.1-pro-high": ("gemini-3.1-pro", 0),
    "gemini-3.1-pro-medium": ("gemini-3.1-pro", 2),
    "gemini-3.1-pro-low": ("gemini-3.1-pro", 4),
}


def _normalize_provider_prefix(model_name: str) -> str:
    requested = model_name.strip()
    vendor, sep, bare = requested.partition("/")
    if sep and vendor.lower() in {"google", "gemini"}:
        return bare.strip() or requested
    return requested


def _apply_model_alias(model_name: str) -> tuple[str, int | None, str | None]:
    requested_name = _normalize_provider_prefix(model_name)
    alias = ANTIGRAVITY_MODEL_ALIASES.get(requested_name.lower())
    if alias is None:
        return requested_name, None, None
    canonical_name, alias_think = alias
    return canonical_name, alias_think, requested_name


def resolve_model(
    model_name: str | None,
    *,
    default: str = DEFAULT_MODEL,
    think_override: int | None = None,
) -> ResolvedModel:
    """Resolve a model name and optional ``@think=N`` suffix."""

    raw_name = (model_name or default).strip() or default
    suffix_think = None
    if "@think=" in raw_name:
        raw_name, think_text = raw_name.rsplit("@think=", 1)
        try:
            suffix_think = int(think_text)
        except ValueError as exc:
            raise ValueError(f"Invalid think level: {think_text}") from exc

    requested_name, alias_think, alias_used = _apply_model_alias(raw_name)

    cfg = MODELS.get(requested_name)
    fallback_used = False
    if cfg is None:
        requested_name, fallback_alias_think, fallback_alias_used = _apply_model_alias(default)
        cfg = MODELS[requested_name]
        if alias_think is None:
            alias_think = fallback_alias_think
        if alias_used is None:
            alias_used = fallback_alias_used
        fallback_used = True

    selected_think = think_override
    if selected_think is None:
        selected_think = suffix_think
    if selected_think is None:
        selected_think = alias_think
    if selected_think is None:
        selected_think = int(cfg["think"])
    if selected_think < 0 or selected_think > 4:
        raise ValueError("think level must be between 0 and 4")

    return ResolvedModel(
        name=requested_name,
        mode=int(cfg["mode"]),
        think=selected_think,
        extra_fields=cfg.get("extra"),
        fallback_used=fallback_used,
        alias_used=alias_used,
    )
