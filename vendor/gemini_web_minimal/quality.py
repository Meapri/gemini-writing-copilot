"""Lightweight output cleanup and source-grounding checks."""

from __future__ import annotations

from dataclasses import dataclass
import re


SOURCE_SENSITIVE_TASKS = {
    "pr-description",
    "release-notes",
    "readme",
    "technical-doc",
    "summarize",
    "translate",
}

META_PREFIX_RE = re.compile(
    r"^(here(?:'s| is)|below is|sure[,!]?|of course[,!]?|다음은|아래는|물론)\b.*?:?\s*$",
    re.IGNORECASE,
)
FACT_RE = re.compile(
    r"(?<![\w.-])(?:v?\d+(?:[._-]\d+){1,3}|\d{4}-\d{1,2}-\d{1,2}|\d+(?:[.,]\d+)?%?)(?![\w.-])"
)
PLACEHOLDER_RE = re.compile(r"\[(?:todo|tbd|fixme|insert|placeholder)[^\]]*\]", re.IGNORECASE)
AI_META_RE = re.compile(r"\b(?:as an ai|language model|i cannot verify|i can't verify)\b", re.IGNORECASE)


@dataclass(frozen=True)
class QualityReport:
    text: str
    issues: tuple[str, ...]


def clean_candidate_output(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    lines = cleaned.splitlines()
    while lines and META_PREFIX_RE.match(lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines).strip()


def resolve_quality_gate(task: str, requested_gate: str, has_source_context: bool) -> str:
    gate = (requested_gate or "auto").lower()
    if gate == "auto":
        return "warn" if has_source_context or task in SOURCE_SENSITIVE_TASKS else "off"
    if gate not in {"off", "warn", "block"}:
        raise ValueError("quality gate must be one of: auto, off, warn, block")
    return gate


def _facts(text: str) -> set[str]:
    return {match.group(0) for match in FACT_RE.finditer(text)}


def review_output(*, text: str, source_text: str = "", context: str = "", task: str = "custom") -> QualityReport:
    cleaned = clean_candidate_output(text)
    issues: list[str] = []
    if not cleaned:
        issues.append("Gemini returned an empty writing result.")
    if AI_META_RE.search(cleaned):
        issues.append("Output contains model meta-commentary that should be removed.")
    if PLACEHOLDER_RE.search(cleaned):
        issues.append("Output still contains unresolved placeholders.")

    source_facts = _facts(source_text + "\n" + context)
    output_facts = _facts(cleaned)
    unsupported = sorted(output_facts - source_facts)
    if unsupported and (source_facts or task in SOURCE_SENSITIVE_TASKS):
        preview = ", ".join(unsupported[:8])
        issues.append(f"Output contains numbers or dates not found in the provided source/context: {preview}")

    return QualityReport(cleaned, tuple(issues))

