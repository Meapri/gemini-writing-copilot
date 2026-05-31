"""Prompt construction for writing-only Gemini calls."""

from __future__ import annotations

TASK_LABELS = {
    "draft": "Write a new draft",
    "rewrite": "Rewrite the provided text",
    "polish": "Polish style and clarity",
    "summarize": "Summarize the provided text",
    "translate": "Translate the provided text",
    "outline": "Create an outline",
    "custom": "Perform the requested writing task",
}

TASK_GUIDANCE = {
    "draft": [
        "Create a complete, usable draft from the brief rather than an outline.",
        "Give the piece a clear opening, coherent progression, and satisfying close.",
        "Use concrete phrasing and avoid generic marketing filler.",
    ],
    "rewrite": [
        "Preserve the original meaning, factual content, and important nuances.",
        "Improve structure, flow, word choice, and readability.",
        "Do not make the result longer unless the instruction asks for expansion.",
    ],
    "polish": [
        "Keep the author's intent and voice, but make the prose smoother and more precise.",
        "Remove awkward phrasing, redundancy, and stiff literal wording.",
        "Prefer natural rhythm over overly formal or decorative language.",
    ],
    "summarize": [
        "Condense the source without adding facts or interpretation not present in it.",
        "Keep the hierarchy of ideas clear and preserve key caveats.",
        "Use bullets only if the requested format calls for them.",
    ],
    "translate": [
        "Translate meaning, tone, and intent rather than word order.",
        "Keep product names, code identifiers, commands, and quoted terms intact unless told otherwise.",
        "Make the target language sound native and natural.",
    ],
    "outline": [
        "Build a useful structure with section headings and concrete talking points.",
        "Make the order easy for a reader to follow.",
        "Include missing-information markers only where the draft cannot proceed responsibly.",
    ],
    "custom": [
        "Follow the user's instruction exactly and choose the most fitting writing form.",
        "When the requested form is ambiguous, produce the most directly usable prose.",
    ],
}

COMPOSITION_PRINCIPLES = [
    "Write for the specified audience and purpose before optimizing for cleverness.",
    "Keep the language of the source unless a target language or translation task says otherwise.",
    "For Korean writing, prefer natural modern Korean with clean sentence endings and no translationese.",
    "Preserve factual claims from the source. Do not invent citations, dates, metrics, names, or commitments.",
    "If required information is missing, mark it briefly in square brackets instead of fabricating it.",
    "Use specific nouns and verbs. Avoid empty intensifiers, vague praise, and boilerplate transitions.",
    "Make paragraph breaks intentional. Each paragraph should move the reader forward.",
    "Return only the requested writing result, without meta commentary or explanation.",
]


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
) -> str:
    task_label = TASK_LABELS.get(task, TASK_LABELS["custom"])
    task_guidance = TASK_GUIDANCE.get(task, TASK_GUIDANCE["custom"])
    variants = max(1, int(variants or 1))

    parts = [
        "You are a writing specialist called by Codex for prose work only.",
        "Your job is to produce finished writing that Codex can review and hand back to the user.",
        "",
        f"Task: {task_label}",
        "",
        "Composition principles:",
        _format_bullets(COMPOSITION_PRINCIPLES),
        "",
        "Task-specific guidance:",
        _format_bullets(task_guidance),
    ]

    if variants > 1:
        parts.extend(
            [
                "",
                f"Produce {variants} distinct options.",
                "Label them as Option 1, Option 2, and so on. Make each option meaningfully different.",
            ]
        )

    _add_section(parts, "Instruction", _clean(instruction))
    _add_section(parts, "Context", _clean(context))
    _add_section(parts, "Tone", _clean(tone))
    _add_section(parts, "Audience", _clean(audience))
    _add_section(parts, "Target language", _clean(target_language))
    _add_section(parts, "Length", _clean(length))
    _add_section(parts, "Style guide", _clean(style_guide))
    _add_section(parts, "Output format", _clean(output_format))
    _add_section(parts, "Source text", _clean(source_text))

    return "\n\n".join(parts).strip()
