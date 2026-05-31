#!/usr/bin/env python3
"""Run deterministic routing acceptance checks for the writing skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "vendor"))

from gemini_web_minimal.routing import infer_task, should_use_writing_skill

DEFAULT_CASES = PLUGIN_ROOT / "evals" / "routing_cases.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate local writing routing heuristics.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    return parser.parse_args()


def load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("routing cases file must contain a JSON array")
    return data


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    cases = load_cases(Path(args.cases).expanduser())
    for index, case in enumerate(cases, 1):
        request = str(case.get("request", ""))
        expected_use = bool(case.get("should_use"))
        expected_task = str(case.get("task", "custom"))
        actual_use = should_use_writing_skill(request)
        actual_task = infer_task(requested_task="auto", instruction=request)
        if actual_use != expected_use:
            failures.append(
                f"case {index}: should_use expected {expected_use}, got {actual_use}: {request}"
            )
        if expected_use and actual_task != expected_task:
            failures.append(f"case {index}: task expected {expected_task}, got {actual_task}: {request}")

    if failures:
        print("Routing eval failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Routing eval passed: {len(cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

