---
name: gemini-writing
description: "Use proactively for prose deliverables: draft, rewrite, polish, translate, summarize, email, announcement, blog, product copy, proposal, docs prose, README text, PR description, release notes, commit or issue summary, and Korean/English tone work. Prefer this skill for style-sensitive wording unless the user says not to use Gemini. Do not use for code implementation, debugging, refactoring decisions, security analysis, or architecture judgment."
---

# Gemini Writing

Use this skill proactively for explicit prose deliverables. Keep ordinary Codex engineering work in Codex.

## Proactive Routing

Default to this skill when the user's requested output is writing, even when the user does not mention Gemini.

Use it for requests that ask Codex to:

- Write, draft, compose, rewrite, polish, improve wording, make text natural, shorten, expand, translate, or summarize prose
- Turn notes, code changes, diffs, issue context, or rough bullets into user-facing text
- Prepare PR descriptions, release notes, commit summaries, README/docs prose, issue summaries, changelog entries, emails, announcements, blog posts, proposals, product copy, or planning documents
- Adjust Korean or English tone, voice, clarity, density, formality, friendliness, or reader fit

Do not wait for the user to say "Gemini" or "use the plugin". Gather the needed local context, run the bundled writer, then review the result before replying. The writer now has `--task auto`, automatic profile defaults, task templates, project-context collection, and a quality gate, so Codex can omit low-confidence options and let the script choose conservative defaults.

If the user asks for code plus prose in one request, keep code implementation and engineering judgment in Codex. Use Gemini only for the prose artifact, such as a PR body, README section, commit summary, or release note.

When a mixed publish flow includes building, committing, tagging, pushing, creating a PR, or creating/editing a GitHub release, route every public-facing prose artifact through this skill before publication. This includes PR bodies, release bodies, `gh release create --notes`, `gh release edit --notes`, changelogs, release summaries, and asset/download descriptions. Gemini drafts or polishes the wording; Codex must then verify all factual claims before publishing.

## When To Use

Use the bundled Gemini writer for:

- Drafting new prose
- Rewriting or polishing existing prose
- Summarizing text
- Translating text
- PR descriptions, release notes, README prose, docs prose
- Emails, announcements, blog posts, planning docs, product copy
- Product copy, proposals, and technical documentation prose

Do not use it for:

- Code generation or code edits
- Debugging or root-cause analysis
- Refactoring strategy
- Security review
- Deciding architecture or API design

## Automatic Option Selection

When the user does not specify options, choose conservative defaults from the request context:

- Email or reply: `--task email`, `--profile email-polite`, `--output-mode final`
- Announcement or notice: `--task announcement`, `--profile chanwoo-ko`, `--output-mode final`
- Blog post or essay: `--task blog`, `--profile chanwoo-ko`, `--structure allow-restructure`
- Product copy: `--task product-copy`, `--profile product-copy-clear`, `--rewrite-strength medium`
- Proposal or planning document: `--task proposal`, `--profile professional-ko`, `--structure allow-restructure`
- PR description, changelog, or issue summary: `--task pr-description`, `--profile github-release`
- Release notes: `--task release-notes`, `--profile github-release`
- README or documentation prose: `--task readme` or `--task technical-doc`, `--profile professional-ko`
- Natural Korean polish: `--task polish`, `--profile chanwoo-ko`, `--preserve-voice medium`
- Formal Korean business prose: `--task polish`, `--profile professional-ko`, `--preserve-voice light`
- Translation: `--task translate`, pass `--target-language` when the user names one
- Multiple alternatives: `--output-mode alternatives`, `--variants 3`
- Edits with rationale: `--output-mode edit-with-notes`
- Change summary only: `--output-mode diff-summary`

Prefer `--length`, `--tone`, `--audience`, and `--style-guide` when the request gives enough signal. If the signal is ambiguous, choose a neutral, useful default instead of asking a setup question.

For repository prose, prefer project context instead of asking the user to paste obvious local state:

- PR descriptions and release notes: use `--project-context auto` or `--project-context git-diff` when diff details matter.
- GitHub release bodies created during build/commit/tag/push flows: use `--task release-notes`, `--profile github-release`, and `--project-context auto`; use `--project-context git-diff` when the diff itself is the main source.
- README/docs/proposals: use `--project-context auto`.
- Sensitive or source-grounded output: keep the default `--quality-gate auto`; use `--quality-gate block` only when unsupported numbers/dates should fail the call.
- Template-sensitive artifacts: keep `--template-mode auto`; use `--template-mode strict` when a recognizable structure is required.

## Script Paths

Resolve paths relative to this skill directory:

- Writer: `../../scripts/gemini_write.py`
- MCP server: `../../scripts/gemini_writing_mcp.py`
- Login helper: `../../scripts/gemini_login.py`
- Doctor: `../../scripts/gemini_doctor.py`

## Tool Path

When the `gemini_write` MCP tool from this plugin is available, prefer it over
manual shell execution. Pass structured arguments instead of building a shell
command, then review the returned draft before replying or publishing.

If the MCP tool is not available in the current Codex session, use the bundled
writer script as the fallback. Do not block the writing workflow just because
the current thread was started before the MCP server was installed or refreshed.

## Login

Default provider: Antigravity (`agy`). Do not use Gemini CLI.

Do not tell the user to type a login command. Run the writer through Antigravity so `agy` opens its own Google login/account chooser if the Antigravity token is missing or stale, then reuses that saved Antigravity login afterward:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_write.py \
  --provider antigravity \
  --task polish \
  --source-text "Text to improve"
```

This path does not read Chrome cookies, does not prompt for macOS Keychain access, and does not use a Chrome extension. The plugin calls `agy --print` and lets Antigravity handle OAuth/token storage.

Use the local Gemini Web cookie login only as a fallback when the user explicitly asks for it:

```bash
GEMINI_WRITING_PROVIDER=web python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_write.py \
  --auto-login \
  --task polish \
  --source-text "Text to improve"
```

For Gemini Web standalone login repair, Codex may run:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py login-standalone
```

If the user explicitly wants to reuse their existing normal Chrome profile for the Gemini Web fallback instead:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py import-chrome-profile
```

If multiple Chrome profiles exist, list them first:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py import-chrome-profile --list-profiles
```

Then import one explicitly:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py login-chrome --profile "Default"
```

Use the local extension bridge only if direct Keychain/Chrome DB import is blocked:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py import-chrome
```

The extension bridge creates a local Chrome extension folder, opens Chrome's extension page and Finder, and starts a localhost receiver. The user must load the extension folder as an unpacked extension, sign into `https://gemini.google.com/app` in their normal Chrome profile, then click the extension button. The extension exports only the required `gemini.google.com` cookies to `127.0.0.1`.

Use the dedicated Playwright profile only when the user does not want to touch their normal Chrome profile:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py start
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py finish
```

Use status/doctor when needed:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_login.py status
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_doctor.py
```

## Writing Calls

Preferred MCP call shape:

```json
{
  "task": "auto",
  "profile": ["chanwoo-ko"],
  "instruction": "Make this concise and professional.",
  "tone": "calm, direct, natural",
  "audience": "the intended reader",
  "project_context": "auto",
  "quality_gate": "auto",
  "template_mode": "auto",
  "output_mode": "final",
  "preserve_voice": "medium",
  "structure": "allow-restructure",
  "rewrite_strength": "medium",
  "source_text": "Text to improve",
  "provider": "antigravity"
}
```

Fallback script call:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_write.py \
  --provider antigravity \
  --task auto \
  --profile chanwoo-ko \
  --instruction "Make this concise and professional." \
  --tone "calm, direct, natural" \
  --audience "the intended reader" \
  --project-context auto \
  --quality-gate auto \
  --template-mode auto \
  --output-mode final \
  --preserve-voice medium \
  --structure allow-restructure \
  --rewrite-strength medium \
  --source-text "Text to improve"
```

Available tasks:

- `auto`
- `email`
- `announcement`
- `blog`
- `pr-description`
- `release-notes`
- `readme`
- `proposal`
- `product-copy`
- `technical-doc`
- `draft`
- `rewrite`
- `polish`
- `summarize`
- `translate`
- `outline`
- `custom`

Optional arguments:

- `--profile`
- `--context`
- `--tone`
- `--audience`
- `--target-language`
- `--length`
- `--style-guide`
- `--output-mode`
- `--preserve-voice`
- `--structure`
- `--rewrite-strength`
- `--variants`
- `--format`
- `--project-context` (`off`, `auto`, `git-summary`, `git-diff`)
- `--project-root`
- `--max-project-context-chars`
- `--quality-gate` (`off`, `auto`, `warn`, `block`)
- `--strict-source` (`auto`, `off`, `on`)
- `--template-mode` (`off`, `auto`, `strict`)
- `--no-auto-profile`
- `--source-file`
- `--model` (Gemini Web fallback only)
- `--think` (Gemini Web fallback only)

The Antigravity provider uses whichever model is configured in `agy`. Model aliases such as `google/gemini-3.1-pro-high`, `gemini-3.5-flash-high`, `gemini-3.5-flash-medium`, and `gemini-3.5-flash-low` are still accepted by the Gemini Web fallback.

Bundled profiles are `chanwoo-ko`, `professional-ko`, `github-release`, `email-polite`, and `product-copy-clear`. User profiles can be added under `~/.config/gemini-writing-copilot/profiles/`.

For `--rewrite-strength`, prefer canonical values `light`, `medium`, or `heavy`. The script also accepts `high` and normalizes it to `heavy` for compatibility, but Codex should use `heavy` in examples and generated commands.

## Response Handling

Do not paste Gemini output blindly. Review it as a draft, then adapt it to the user's exact request, local context, tone, and factual constraints.

If Gemini invents facts, citations, dates, numbers, or claims not present in the input, remove them or mark them as unknown.

For publishing prose, Codex remains responsible for facts. Before creating or editing a PR/release body, verify versions, tag names, commit hashes, test results, artifact names, checksums, links, dates, and any user-impact claims against local commands or GitHub output. Remove or correct anything Gemini inferred without evidence.

If the request asks for final prose only, return final prose only. If the user asks for alternatives, produce a concise set of alternatives.

Codex review checklist:

- Does the output follow the requested format strictly?
- Are all factual claims from the source preserved?
- Is the tone appropriate for the selected profile?
- Are there any missing placeholders that need user attention?
- Is the text free of conversational filler?

Prefer passing `--profile`, `--tone`, `--audience`, `--length`, `--output-mode`, `--preserve-voice`, `--structure`, `--rewrite-strength`, and `--style-guide` when the user's request includes enough context. Use `--variants` only when the user asks for multiple options or when alternatives are clearly useful.
