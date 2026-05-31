# Usage

Gemini Writing Copilot should be used only for explicit prose work. Codex keeps
engineering decisions, code edits, debugging, security review, and architecture
judgment in Codex.

## Basic Calls

```bash
python3 scripts/gemini_write.py \
  --task polish \
  --profile chanwoo-ko \
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

## Output Handling

The Gemini result is a candidate draft. Codex should review it for:

- requested format
- factual preservation
- profile/tone fit
- missing placeholders
- conversational filler

Codex should return the final user-facing prose, not the raw Gemini output when
the raw output needs cleanup.
