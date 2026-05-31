"""Prompt construction for writing-only Gemini calls."""

from __future__ import annotations

from .writing_guidance import (
    GENERAL_WRITING_GUIDANCE,
    OUTPUT_MODE_GUIDANCE,
    PRESERVE_VOICE_GUIDANCE,
    REWRITE_STRENGTH_GUIDANCE,
    STRUCTURE_MODE_GUIDANCE,
    TASK_GUIDANCE,
    TASK_LABELS,
    normalize_rewrite_strength,
)
from .writing_templates import POSITIONING_LINE, TASK_TEMPLATES


def _clean(value: object) -> str:
    return str(value or "").strip()


def _add_section(parts: list[str], title: str, body: str) -> None:
    if body.strip():
        parts.append(f"{title}:\n{body.strip()}")


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def build_writing_prompt(
    *,
    task: str,
    instruction: str = "",
    source_text: str = "",
    context: str = "",
    tone: str = "",
    audience: str = "",
    target_language: str = "",
    output_format: str = "",
    style_guide: str = "",
    length: str = "",
    variants: int = 1,
    output_mode: str = "final",
    preserve_voice: str = "medium",
    structure_mode: str = "allow-restructure",
    rewrite_strength: str = "medium",
    task_template: str | None = "",
    project_context: str = "",
    strict_source: bool = False,
) -> str:
    task_label = TASK_LABELS.get(task, TASK_LABELS["custom"])
    task_guidance = TASK_GUIDANCE.get(task, TASK_GUIDANCE["custom"])
    output_mode_guidance = OUTPUT_MODE_GUIDANCE.get(output_mode, OUTPUT_MODE_GUIDANCE["final"])
    preserve_voice_guidance = PRESERVE_VOICE_GUIDANCE.get(preserve_voice, PRESERVE_VOICE_GUIDANCE["medium"])
    structure_guidance = STRUCTURE_MODE_GUIDANCE.get(structure_mode, STRUCTURE_MODE_GUIDANCE["allow-restructure"])
    rewrite_strength = normalize_rewrite_strength(rewrite_strength)
    rewrite_guidance = REWRITE_STRENGTH_GUIDANCE.get(rewrite_strength, REWRITE_STRENGTH_GUIDANCE["medium"])
    variants = max(1, int(variants or 1))

    parts = [
        "You are a writing specialist called by Codex for prose work only.",
        "Your job is to produce finished writing that Codex can review and hand back to the user.",
        "",
        "Plugin positioning:",
        POSITIONING_LINE,
        "",
        f"Task: {task_label}",
        "",
        "Composition principles:",
        _format_bullets(GENERAL_WRITING_GUIDANCE),
        "",
        "Task-specific guidance:",
        _format_bullets(task_guidance),
    ]

    if task_template is not None:
        template = task_template.strip()
        if not template and task in TASK_TEMPLATES:
            template = _format_bullets(TASK_TEMPLATES[task])
        if template:
            parts.extend(["", "Task template:", template])

    if strict_source:
        parts.extend(
            [
                "",
                "Source-grounding contract:",
                _format_bullets(
                    [
                        "Do not invent features, dates, numbers, tests, names, links, or claims not present in the source/context.",
                        "Use placeholders in square brackets when required facts are missing.",
                        "Preserve uncertainty instead of making unsupported claims sound certain.",
                    ]
                ),
            ]
        )

    parts.extend(
        [
            "",
            "Output contract:",
            output_mode_guidance,
            "",
            "Voice preservation:",
            preserve_voice_guidance,
            "",
            "Structure mode:",
            structure_guidance,
            "",
            "Rewrite strength:",
            rewrite_guidance,
        ]
    )

    if variants > 1:
        _add_section(parts, "Requested variants", str(variants))

    _add_section(parts, "Instruction", _clean(instruction))
    _add_section(parts, "Context", _clean(context))
    _add_section(parts, "Tone", _clean(tone))
    _add_section(parts, "Audience", _clean(audience))
    _add_section(parts, "Target language", _clean(target_language))
    _add_section(parts, "Length", _clean(length))
    _add_section(parts, "Style guide", _clean(style_guide))
    _add_section(parts, "Output format", _clean(output_format))
    _add_section(parts, "Project context", _clean(project_context))
    _add_section(parts, "Source text", _clean(source_text))

    return "\n\n".join(parts).strip()
