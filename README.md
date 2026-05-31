# Gemini Writing Copilot

Codex personal plugin that calls Antigravity/Gemini only for explicit writing tasks.

The default provider is Google Antigravity's local `agy` CLI. This plugin does
not use the Gemini CLI. Antigravity owns the Google login, account chooser,
OAuth token refresh, and token storage; the plugin only sends a writing prompt
through `agy --print` and returns the generated prose.

The built-in writing guidance and style profiles were generated with Gemini
3.1 Pro High and committed as deterministic defaults.

## What Is Included

- `skills/gemini-writing/SKILL.md`: routing instructions for Codex
- `scripts/gemini_write.py`: writing-only Gemini/Antigravity caller
- `scripts/gemini_login.py`: legacy Gemini Web cookie login fallback
- `scripts/gemini_doctor.py`: local diagnostics
- `vendor/gemini_web_minimal/`: minimal provider code adapted from `Sophomoresty/gemini-web2api` and Antigravity patterns from `Meapri/hermes-google-antigravity-plugin`

No MCP server is included.

## Install

```bash
git clone https://github.com/Meapri/gemini-writing-copilot.git
cd gemini-writing-copilot
codex plugin marketplace add "$(pwd)"
codex plugin add gemini-writing-copilot@gemini-writing-copilot
```

Then start a new Codex thread so the skill is loaded.

More details:

- [Install](docs/install.md)
- [Usage](docs/usage.md)
- [Security](docs/security.md)

## Setup

Requires Python 3.9 or newer.

### Default: Antigravity Login

Install/open Google Antigravity so `agy` is available. The recommended writing
model is `Gemini 3.1 Pro (High)`. On first use,
Antigravity opens its own Google login/account chooser and stores its OAuth
token under its normal local Antigravity profile. Later calls reuse that login.

```bash
python3 scripts/gemini_write.py --task polish --source-text "Draft text"
```

Health check:

```bash
python3 scripts/gemini_doctor.py
```

### Fallback: Gemini Web Cookie Login

The old Gemini Web cookie provider is still present for repair/testing, but it
is no longer the default path. Force it only when needed:

```bash
GEMINI_WRITING_PROVIDER=web python3 scripts/gemini_write.py --auto-login --task polish --source-text "Draft text"
```

Cookie login options remain available:

- `python3 scripts/gemini_login.py login-standalone`
- `python3 scripts/gemini_login.py login-chrome`
- `python3 scripts/gemini_login.py import-chrome-profile`
- `python3 scripts/gemini_login.py import-chrome`
- `python3 scripts/gemini_login.py start` / `finish`

## Usage

```bash
python3 scripts/gemini_write.py \
  --provider antigravity \
  --task blog \
  --instruction "Make this warmer and more concise." \
  --profile chanwoo-ko \
  --tone "calm, direct, natural" \
  --audience "maintainers" \
  --length "two short paragraphs" \
  --style-guide "Plain language. No hype." \
  --output-mode final \
  --preserve-voice medium \
  --structure allow-restructure \
  --rewrite-strength medium \
  --source-text "Draft text here"
```

Useful composition controls:

- `--task`: `draft`, `rewrite`, `polish`, `summarize`, `translate`, `outline`,
  `email`, `announcement`, `blog`, `pr-description`, `release-notes`, `readme`,
  `proposal`, `product-copy`, `technical-doc`, or `custom`
- `--profile`: bundled or user style profile
- `--tone`: voice and emotional register
- `--audience`: target reader
- `--length`: desired length or density
- `--style-guide`: house style, do/don't rules, or examples to follow
- `--output-mode`: `final`, `alternatives`, `edit-with-notes`, or `diff-summary`
- `--preserve-voice`: `off`, `light`, `medium`, or `strong`
- `--structure`: `preserve`, `allow-restructure`, or `restructure`
- `--rewrite-strength`: `light`, `medium`, or `heavy`
- `--variants`: number of distinct alternatives to generate

Bundled style profiles:

- `chanwoo-ko`
- `professional-ko`
- `github-release`
- `email-polite`
- `product-copy-clear`

User profiles can be placed under:

```text
~/.config/gemini-writing-copilot/profiles/
```

## Configuration

Environment variables:

- `GEMINI_WRITING_PROVIDER` (`antigravity`, `web`, or `auto`; default `antigravity`)
- `GEMINI_WRITING_AGY_BIN`
- `GEMINI_WRITING_COOKIE_FILE`
- `GEMINI_WRITING_MODEL` (Gemini Web fallback only; Antigravity uses the model configured in `agy`)
- `GEMINI_WRITING_THINK` (Gemini Web fallback only)
- `GEMINI_WRITING_TIMEOUT_SEC`
- `GEMINI_WRITING_PROXY`
- `GEMINI_WRITING_STYLE_PROFILE_DIR`
- `HTTPS_PROXY`

Optional config file:

```text
~/.config/gemini-writing-copilot/config.json
```

## Notes

Gemini output should be treated as a writing draft. Codex should review it before returning a final answer.
