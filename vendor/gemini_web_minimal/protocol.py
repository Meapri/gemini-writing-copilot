"""Gemini Web StreamGenerate payload and response parsing."""

from __future__ import annotations

import json
import re
import urllib.parse
import uuid

DEFAULT_GEMINI_BL = "boq_assistant-bard-web-server_20260525.09_p0"


def build_payload(
    prompt: str,
    *,
    model_id: int,
    think_mode: int,
    extra_fields: dict[int, object] | None = None,
) -> str:
    """Build the ``f.req`` form body for Gemini Web StreamGenerate."""

    inner: list[object | None] = [None] * 102
    inner[0] = [prompt, 0, None, None, None, None, 0]
    inner[1] = ["en"]
    inner[2] = ["", "", "", None, None, None, None, None, None, ""]
    inner[6] = [0]
    inner[7] = 1
    inner[10] = 1
    inner[11] = 0
    inner[17] = [[think_mode]]
    inner[18] = 0
    inner[27] = 1
    inner[30] = [4]
    inner[41] = [2]
    inner[53] = 0
    inner[59] = str(uuid.uuid4())
    inner[61] = []
    inner[68] = 1
    inner[79] = model_id
    if extra_fields:
        for key, value in extra_fields.items():
            inner[int(key)] = value
    outer = [None, json.dumps(inner, ensure_ascii=False)]
    return urllib.parse.urlencode({"f.req": json.dumps(outer, ensure_ascii=False)})


def build_stream_generate_url(*, gemini_bl: str = DEFAULT_GEMINI_BL, reqid: int) -> str:
    return (
        "https://gemini.google.com/_/BardChatUi/data/"
        "assistant.lamda.BardFrontendService/StreamGenerate"
        f"?bl={urllib.parse.quote(gemini_bl)}&hl=en&_reqid={reqid}&rt=c"
    )


def clean_text(text: str) -> str:
    text = re.sub(
        r"```(?:python|javascript|text)\?code_(?:reference|stdout)&code_event_index=\d+\n.*?```\n?",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"http://googleusercontent\.com/card_content/\d+\n?", "", text)
    return text.strip()


def extract_texts_from_line(line: str) -> list[str]:
    if '"wrb.fr"' not in line or len(line) < 200:
        return []
    try:
        arr = json.loads(line)
        inner_str = arr[0][2]
        if not inner_str or len(inner_str) < 50:
            return []
        inner = json.loads(inner_str)
        if not (isinstance(inner, list) and len(inner) > 4 and inner[4]):
            return []
        texts: list[str] = []
        for part in inner[4]:
            if isinstance(part, list) and len(part) > 1 and isinstance(part[1], list):
                for value in part[1]:
                    if isinstance(value, str) and value:
                        texts.append(value)
        return texts
    except (json.JSONDecodeError, IndexError, TypeError):
        return []


def extract_response_text(raw: str) -> str:
    last_text = ""
    for line in raw.splitlines():
        for text in extract_texts_from_line(line):
            if len(text) > len(last_text):
                last_text = text
    return clean_text(last_text)
