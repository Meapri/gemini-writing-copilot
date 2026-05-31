---
name: gemini-writing
description: "Use when the user explicitly asks for writing help that benefits from Gemini: drafting, rewriting, polishing tone, summarizing, translating, release notes, PR descriptions, README prose, emails, announcements, blog posts, or planning documents. Do not use for code implementation, debugging, refactoring decisions, security analysis, or architecture judgment."
---

# Gemini Writing

Use this skill only for explicit writing work. Keep ordinary Codex engineering work in Codex.

## When To Use

Use the bundled Gemini writer for:

- Drafting new prose
- Rewriting or polishing existing prose
- Summarizing text
- Translating text
- PR descriptions, release notes, README prose, docs prose
- Emails, announcements, blog posts, planning docs, product copy

Do not use it for:

- Code generation or code edits
- Debugging or root-cause analysis
- Refactoring strategy
- Security review
- Deciding architecture or API design

## Script Paths

Resolve paths relative to this skill directory:

- Writer: `../../scripts/gemini_write.py`
- Login helper: `../../scripts/gemini_login.py`
- Doctor: `../../scripts/gemini_doctor.py`

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

Call Gemini through the script and read stdout as the candidate writing result:

```bash
python3 /Users/naen/plugins/gemini-writing-copilot/scripts/gemini_write.py \
  --provider antigravity \
  --task polish \
  --instruction "Make this concise and professional." \
  --tone "calm, direct, natural" \
  --audience "the intended reader" \
  --source-text "Text to improve"
```

Available tasks:

- `draft`
- `rewrite`
- `polish`
- `summarize`
- `translate`
- `outline`
- `custom`

Optional arguments:

- `--context`
- `--tone`
- `--audience`
- `--target-language`
- `--length`
- `--style-guide`
- `--variants`
- `--format`
- `--source-file`
- `--model` (Gemini Web fallback only)
- `--think` (Gemini Web fallback only)

The Antigravity provider uses whichever model is configured in `agy`. Model aliases such as `google/gemini-3.1-pro-high`, `gemini-3.5-flash-high`, `gemini-3.5-flash-medium`, and `gemini-3.5-flash-low` are still accepted by the Gemini Web fallback.

## Response Handling

Do not paste Gemini output blindly. Review it as a draft, then adapt it to the user's exact request, local context, tone, and factual constraints.

If Gemini invents facts, citations, dates, numbers, or claims not present in the input, remove them or mark them as unknown.

If the request asks for final prose only, return final prose only. If the user asks for alternatives, produce a concise set of alternatives.

Prefer passing `--tone`, `--audience`, `--length`, and `--style-guide` when the user's request includes enough context. Use `--variants` only when the user asks for multiple options or when alternatives are clearly useful.
