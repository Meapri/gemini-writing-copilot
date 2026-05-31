# Security

Gemini Writing Copilot is a local plugin. It does not run a server and does not
include an MCP server.

## Default Authentication

The default provider is Google Antigravity through the local `agy` CLI.

- The plugin does not use Gemini CLI.
- The plugin does not read Chrome cookies in the default path.
- The plugin does not ask for macOS Keychain access in the default path.
- Antigravity handles Google login, account selection, token refresh, and token
  storage.
- The plugin sends writing prompts to `agy --print`.

## Gemini Web Cookie Fallback

The legacy Gemini Web fallback is still present for explicit repair/testing.
It is not the default path.

Fallback commands may store a cookie bundle at:

```text
~/.config/gemini-writing-copilot/cookie.json
```

That file is written with `0600` permissions. Do not commit it.

## Sensitive Data

Do not place secrets in:

- prompts
- style profiles
- config files
- screenshots
- issue reports

The repository `.gitignore` excludes common local secret and cache files, but
users are responsible for reviewing local changes before publishing.

## Project Context

`--project-context auto` is designed to send a safe repository summary for
source-sensitive prose tasks: git status, changed file names, diff stats, recent
commit subjects, and short metadata excerpts. It does not include full patch
content.

`--project-context git-diff` includes patch excerpts and can contain private
implementation details or accidentally committed secrets. Use it only when the
writing task needs patch-level context.

## Network Behavior

Default writing requests are sent through Antigravity's configured provider.
Gemini Web fallback requests go to Gemini Web endpoints only when explicitly
selected.

## Reporting Issues

When reporting bugs, include:

- command used
- task/profile/options
- sanitized stderr
- `gemini_doctor.py` output with secrets removed

Never include cookies, OAuth tokens, authorization headers, or private draft
content.
