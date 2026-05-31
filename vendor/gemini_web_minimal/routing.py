"""Deterministic routing helpers for writing tasks."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RouteDefaults:
    task: str
    profiles: tuple[str, ...] = ()
    output_mode: str = "final"
    preserve_voice: str = "medium"
    structure_mode: str = "allow-restructure"
    rewrite_strength: str = "medium"


TASK_DEFAULTS = {
    "email": RouteDefaults("email", ("email-polite",), preserve_voice="light"),
    "announcement": RouteDefaults("announcement", ("chanwoo-ko",)),
    "blog": RouteDefaults("blog", ("chanwoo-ko",), structure_mode="allow-restructure"),
    "pr-description": RouteDefaults("pr-description", ("github-release",), preserve_voice="light"),
    "release-notes": RouteDefaults("release-notes", ("github-release",), preserve_voice="light"),
    "readme": RouteDefaults("readme", ("professional-ko",), structure_mode="allow-restructure"),
    "proposal": RouteDefaults("proposal", ("professional-ko",), structure_mode="allow-restructure"),
    "product-copy": RouteDefaults("product-copy", ("product-copy-clear",)),
    "technical-doc": RouteDefaults("technical-doc", ("professional-ko",), preserve_voice="light"),
    "summarize": RouteDefaults("summarize", ("professional-ko",), rewrite_strength="light"),
    "translate": RouteDefaults("translate", ("professional-ko",), preserve_voice="strong"),
    "polish": RouteDefaults("polish", ("chanwoo-ko",)),
    "rewrite": RouteDefaults("rewrite", ("chanwoo-ko",), rewrite_strength="medium"),
    "outline": RouteDefaults("outline", ("professional-ko",), preserve_voice="light"),
    "draft": RouteDefaults("draft", ("professional-ko",)),
    "custom": RouteDefaults("custom"),
}

TASK_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pr-description", ("pr description", "pull request", "merge request", "pr body", "pr 설명", "풀리퀘", "풀 리퀘", "리뷰어")),
    ("release-notes", ("release notes", "changelog", "릴리즈노트", "릴리즈 노트", "변경 로그", "배포 노트")),
    ("readme", ("readme", "리드미")),
    ("technical-doc", ("technical doc", "documentation", "docs", "문서화", "기술 문서", "사용법 문서")),
    ("email", ("email", "e-mail", "메일", "이메일", "답장")),
    ("announcement", ("announcement", "notice", "공지", "안내문", "알림문")),
    ("blog", ("blog", "post", "essay", "블로그", "글 써", "글쓰기")),
    ("proposal", ("proposal", "plan doc", "planning doc", "기획서", "제안서", "계획서")),
    ("polish", ("polish", "improve wording", "make it natural", "윤문", "다듬", "자연스럽", "톤 보정", "문장 개선")),
    ("product-copy", ("product copy", "landing copy", "marketing copy", "카피", "홍보 문구", "마케팅 문구")),
    ("translate", ("translate", "translation", "번역", "영어로", "한국어로", "일본어로", "중국어로")),
    ("summarize", ("summarize", "summary", "요약", "정리해", "줄여서")),
    ("outline", ("outline", "목차", "개요", "아웃라인")),
    ("rewrite", ("rewrite", "다시 써", "고쳐 써", "문체 바꿔")),
    ("draft", ("draft", "compose", "write", "작성", "초안", "써줘")),
)

WRITING_POSITIVE_PATTERNS = (
    "write",
    "draft",
    "compose",
    "rewrite",
    "polish",
    "translate",
    "summarize",
    "release notes",
    "pr description",
    "readme",
    "email",
    "announcement",
    "blog",
    "proposal",
    "product copy",
    "tone",
    "wording",
    "작성",
    "써줘",
    "초안",
    "문장",
    "문체",
    "윤문",
    "다듬",
    "번역",
    "요약",
    "릴리즈",
    "공지",
    "메일",
    "카피",
    "문서화",
)

ENGINEERING_NEGATIVE_PATTERNS = (
    "debug",
    "fix bug",
    "implement",
    "refactor",
    "architecture",
    "security",
    "root cause",
    "코드 구현",
    "디버깅",
    "리팩터",
    "아키텍처",
    "보안",
    "근본 원인",
)


def _haystack(*values: str) -> str:
    return "\n".join(value for value in values if value).lower()


def infer_task(*, requested_task: str, instruction: str = "", source_text: str = "", context: str = "") -> str:
    if requested_task not in {"", "auto", "custom"}:
        return requested_task

    text = _haystack(instruction, context, source_text[:1000])
    for task, patterns in TASK_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return task
    return "polish" if source_text.strip() else "draft"


def defaults_for_task(task: str) -> RouteDefaults:
    return TASK_DEFAULTS.get(task, TASK_DEFAULTS["custom"])


def should_use_writing_skill(request: str) -> bool:
    text = request.lower()
    positive = any(pattern in text for pattern in WRITING_POSITIVE_PATTERNS)
    if not positive:
        return False
    if any(pattern in text for pattern in ENGINEERING_NEGATIVE_PATTERNS):
        prose_artifact = re.search(
            r"(pr description|release notes|readme|docs|documentation|문서|릴리즈|pr 설명)",
            text,
        )
        return bool(prose_artifact)
    return True
