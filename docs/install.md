# Install

Gemini Writing Copilot is distributed as a local Codex plugin. The easiest
public install path is to clone this repository and add it as a local
marketplace.

## Requirements

- Codex desktop with plugin support
- Python 3.9 or newer
- Google Antigravity with the `agy` CLI installed
- A Google account signed in through Antigravity

## Install From GitHub

```bash
git clone https://github.com/Meapri/gemini-writing-copilot.git
cd gemini-writing-copilot
codex plugin marketplace add "$(pwd)"
codex plugin add gemini-writing-copilot@gemini-writing-copilot
```

The repository includes `.agents/plugins/marketplace.json`, so the repo root can
act as the marketplace root.

## Verify

```bash
python3 scripts/gemini_doctor.py
python3 scripts/gemini_write.py --task polish --source-text "Draft text"
```

`gemini_doctor.py` should report:

```text
Provider: antigravity
Antigravity generation check: ok
```

## Personal Marketplace Install

If you prefer the default personal marketplace, clone the repository under
`~/plugins`:

```bash
mkdir -p ~/plugins
git clone https://github.com/Meapri/gemini-writing-copilot.git ~/plugins/gemini-writing-copilot
```

Then make sure `~/.agents/plugins/marketplace.json` contains this entry:

```json
{
  "name": "gemini-writing-copilot",
  "source": {
    "source": "local",
    "path": "./plugins/gemini-writing-copilot"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_USE"
  },
  "category": "Productivity"
}
```

Install it with:

```bash
codex plugin add gemini-writing-copilot@personal
```

## Updating

```bash
cd gemini-writing-copilot
git pull
codex plugin add gemini-writing-copilot@gemini-writing-copilot
```

Start a new Codex thread after updating so the refreshed skill is loaded.
