# Usage

Gemini Writing Copilot should be used proactively whenever the requested
deliverable is prose. The user does not need to mention Gemini; Codex should
select this skill for writing artifacts and keep engineering decisions, code
edits, debugging, security review, and architecture judgment in Codex.

Typical proactive triggers include PR descriptions, release notes, README or
docs prose, commit summaries, issue summaries, emails, announcements, blog
posts, proposals, product copy, translation, summarization, and Korean/English
tone polishing.

The CLI can also infer conservative defaults with `--task auto`. It selects a
task, default profile, template guidance, source-grounding behavior, and safe
project context mode where appropriate.

## MCP Tool

Fresh Codex sessions with the plugin installed expose a `gemini_write` MCP tool.
Use it for structured writing calls when available. The tool is a wrapper around
the same local writer, so outputs remain drafts that Codex must review.

Typical tool arguments:

```json
{
  "task": "auto",
  "instruction": "Make this warmer and more concise.",
  "source_text": "Draft text",
  "tone": "calm, direct, natural",
  "project_context": "auto",
  "quality_gate": "auto",
  "provider": "antigravity"
}
```

If the MCP tool is not available in the current thread, use the CLI fallback
below. This can happen when the thread started before the plugin was refreshed.

## Basic Calls

```bash
python3 scripts/gemini_write.py \
  --task auto \
  --source-text "Draft text"
```

```bash
python3 scripts/gemini_write.py \
  --task email \
  --profile email-polite \
  --instruction "Ask to move the meeting to next week." \
  --tone "polite and concise Korean"
```

## Writing Tasks

- `auto`
- `draft`
- `rewrite`
- `polish`
- `summarize`
- `translate`
- `outline`
- `email`
- `announcement`
- `blog`
- `pr-description`
- `release-notes`
- `readme`
- `proposal`
- `product-copy`
- `technical-doc`
- `custom`

## Automatic Routing

Use `--task auto` when the calling skill has enough natural-language signal but
does not need to choose every option itself. The script infers tasks such as
`pr-description`, `release-notes`, `readme`, `email`, `translate`, `summarize`,
`product-copy`, and `polish`.

Run the local routing acceptance set:

```bash
python3 scripts/evaluate_routing.py
```

## Style Profiles

Bundled profiles:

- `chanwoo-ko`
- `professional-ko`
- `github-release`
- `email-polite`
- `product-copy-clear`

Use one or more profiles with repeated `--profile` arguments:

```bash
python3 scripts/gemini_write.py \
  --task release-notes \
  --profile github-release \
  --context "Added Antigravity provider and writing profiles."
```

User profiles can be stored under:

```text
~/.config/gemini-writing-copilot/profiles/
```

Then call them by filename without `.md`:

```bash
python3 scripts/gemini_write.py --task rewrite --profile my-house-style --source-file draft.md
```

## Composition Controls

- `--tone`: voice and emotional register
- `--audience`: intended reader
- `--length`: desired length or density
- `--style-guide`: extra style instructions
- `--output-mode`: `final`, `alternatives`, `edit-with-notes`, or `diff-summary`
- `--preserve-voice`: `off`, `light`, `medium`, or `strong`
- `--structure`: `preserve`, `allow-restructure`, or `restructure`
- `--rewrite-strength`: `light`, `medium`, or `heavy`
- `--variants`: number of distinct alternatives
- `--project-context`: `auto`, `off`, `git-summary`, or `git-diff`
- `--quality-gate`: `auto`, `off`, `warn`, or `block`
- `--strict-source`: `auto`, `off`, or `on`
- `--template-mode`: `auto`, `off`, or `strict`
- `--no-auto-profile`: skip automatic profile selection

`--rewrite-strength high` is accepted as a compatibility alias for `heavy`.
Prefer `heavy` in documented commands.

## Project Context

For source-sensitive tasks, `--project-context auto` collects a safe git summary
from the local repo: status, changed file names, diff stats, recent commits, and
small metadata excerpts such as README or plugin manifest content.

Use `--project-context git-diff` only when Gemini needs patch-level details.
The diff is truncated by `--max-project-context-chars`.

## Quality Gate

`--quality-gate auto` cleans common model preambles and warns when the output
contains unresolved placeholders, model meta-commentary, or numbers/dates not
present in the provided source/context. Use `--quality-gate block` for stricter
source-grounded artifacts.

## Templates

`--template-mode auto` injects Gemini-authored task templates for common writing
artifacts. Use `--template-mode strict` when a recognizable structure is more
important than freeform prose.

## Output Handling

The Gemini result is a candidate draft. Codex should review it for:

- requested format
- factual preservation
- profile/tone fit
- missing placeholders
- conversational filler

Codex should return the final user-facing prose, not the raw Gemini output when
the raw output needs cleanup.
