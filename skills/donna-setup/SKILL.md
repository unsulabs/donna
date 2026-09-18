---
name: donna-setup
description: Use when installing or finishing a Donna Hermes profile — full-stack first-run setup matching the reference Donna stack (identity, Mnemosyne, PARA Obsidian vault, daily briefing, TTS, optional Google/Telegram). Consent-gated; no secrets in chat.
version: 1.0.0
author: Unsu Labs
license: MIT
platforms:
  - linux
  - macos
  - windows
metadata:
  hermes:
    tags:
      - donna
      - hermes
      - onboarding
      - mnemosyne
      - obsidian
      - vault
      - cron
    related_skills:
      - hermes-starter-onboarding
      - hermes-mnemosyne
      - obsidian
      - vault-organization
      - google-workspace
---

# Donna full-stack setup

Turn a freshly installed **Donna** profile into the same operating stack as the reference configuration:

| Layer | Target state |
|---|---|
| Persona | `SOUL.md` / `AGENTS.md` already shipped |
| Memory | **Mnemosyne**, profile-scoped DB, `auto_sleep: false`, host LLM enabled |
| Notes | Dedicated **Obsidian** vault, **PARA + Daily + Inbox**, templates, `.obsidian` config |
| Rhythm | Optional **Daily Briefing** cron (user picks time/timezone) |
| Voice | **Edge TTS** (no key), voice chosen with user |
| Messaging | Optional Telegram (user supplies bot token via `.env`, never chat) |
| Google | Optional Workspace OAuth via `google-workspace` skill (user browser consent) |

This skill is the **Donna-specific** orientation. The generic `hermes-starter-onboarding` skill remains valid for lighter setups; prefer **this** skill when the user wants “Donna like the reference stack.”

## Hard rules

1. **Consent-gated.** Show a plan; apply only after explicit approval.
2. **No secrets in chat.** Never ask for API keys, bot tokens, OAuth codes, or passwords in the conversation. Point to `.env` / official device flows / browser consent.
3. **Profile-local only.** Write only the active profile unless the user explicitly widens scope.
4. **No personal defaults from the package author.** Ask for name, timezone, vault path, city, language.
5. **Do not restart the gateway from inside the gateway.** Tell the user the exact external command if a restart is required.
6. **Run orientation in the live session** — do not delegate onboarding to a sub-agent.
7. **Mnemosyne is a memory provider, not a toolset.** Never `enabled_toolsets: ["mnemosyne"]`.

## Phase 0 — Inspect

Before changing anything:

```bash
hermes memory status
hermes config get memory.provider || true
hermes config get memory.auto_sleep || true
cronjob list   # via tool: cronjob(action="list")
```

Resolve:

- Active profile home (`HERMES_HOME` / `~/.hermes/profiles/<name>`)
- Whether `OBSIDIAN_VAULT_PATH` is already set (name only; do not dump `.env`)
- Whether a vault path already exists on disk

Report starting state in 5–8 lines. No credential values.

## Phase 1 — Questions (continuous pass)

Ask in small groups; do not stop after identity.

### 1. Identity
- What should I call you?
- What do you call me? (default **Donna**)
- Reply style: concise / conversational / formal / detailed?

### 2. Locale
- IANA timezone (e.g. `America/Mexico_City`, `Europe/Madrid`, `UTC`)
- Default city for weather (optional)
- Preferred TTS language/voice (defaults: `en-US-JennyNeural` or `es-MX-DaliaNeural` if Spanish)

### 3. Memory
Recommend **Mnemosyne** (local, profile-scoped). Confirm install path with current Hermes docs if needed.

### 4. Obsidian vault
- Create a **new dedicated** vault for this profile? (recommended — do not mix with a personal everything-vault)
- Absolute path, e.g. `~/Documents/Donna-Vault` — expand and store as absolute in `.env`
- If they already have a path, use it only after they name it; do not scan arbitrary home folders for notes

### 5. Daily briefing
- Want it? Time + timezone + sections (tasks/weather/agenda if calendar later)
- Delivery: omit `deliver` for origin chat unless they specify otherwise

### 6. Optional integrations
- Telegram bot? → user edits `.env` themselves
- Google Workspace (Gmail/Calendar/Drive)? → run `google-workspace` setup; browser OAuth gate
- Config guardian cron (restore model keys if desktop login overwrites)? only if they set expected provider/model

### 7. Toolsets
CLI toolsets ship enabled. Walk plain-language list and peel back only what they decline (same table as `hermes-starter-onboarding`).

## Phase 2 — Plan

```text
Proposed Donna setup
Identity: <user> / <assistant> / <style>
Timezone: <iana> · Weather city: <or none>
Memory: Mnemosyne @ <profile>/mnemosyne/data · auto_sleep false · host LLM on
Vault: scaffold PARA at <abs path> · OBSIDIAN_VAULT_PATH
TTS: edge / <voice>
Briefing: <schedule or none>
Optional: Telegram / Google / config guard
Toolsets off: <list or none>
I will not write secrets or connect accounts until you approve.
```

Require clear approval.

## Phase 3 — Apply (order)

### A. Identity + style
Write profile-local `memories/USER.md` fields and Mnemosyne canonical/preferences only after approval. Update `MEMORY.md` stack section with non-secret paths.

### B. Timezone
```bash
hermes config set timezone '<IANA>'
```

### C. Mnemosyne
1. Ensure plugin installed per current upstream (`hermes memory status`; if missing, follow current `mnemosyne-hermes` / Hermes plugin docs — do not invent package names).
2. Create data dir: `$HERMES_HOME/mnemosyne/data` (absolute).
3. Set in profile `.env` **without printing values**:
   - `MNEMOSYNE_DATA_DIR=<absolute>`
   - `MNEMOSYNE_HOST_LLM_ENABLED=true`
4. ```bash
   hermes config set memory.memory_enabled true
   hermes config set memory.provider mnemosyne
   hermes config set memory.auto_sleep false
   hermes config set memory.write_approval true
   ```
5. Verify: `hermes memory status` → provider mnemosyne available. Optional smoke: store + recall a disposable test fact, then delete/invalidate if appropriate.

**Cross-profile warning:** some Mnemosyne installers link every profile. Prefer profile-scoped wrapper install; if a global installer is required, get explicit approval first.

### D. Obsidian vault
1. Run the shipped scaffold (from the distribution root or profile copy of scripts):

```bash
python3 "$HERMES_HOME/scripts/scaffold_vault.py" --vault '<ABS_VAULT>'
# or from a checkout:
python3 scripts/scaffold_vault.py --vault '<ABS_VAULT>'
```

If scripts were not copied into the profile, run from the git checkout path the user installed from, or copy `assets/vault-starter` + `scripts/scaffold_vault.py` into the profile first.

2. Set `OBSIDIAN_VAULT_PATH=<ABS_VAULT>` in profile `.env` (absolute path; no `~`).
3. Verify: `Home.md`, `MOC.md`, `Inbox.md`, `.obsidian/daily-notes.json` exist.
4. Linux Flatpak (optional, if Obsidian Flatpak present):
   - filesystem override for the vault path only
   - optional desktop entry `obsidian://open?path=...`
5. Tell the user to open the vault once in Obsidian to register it.

Daily notes contract:
- folder `Daily`
- format `YYYY/MM/YYYY-MM-DD`
- template `Resources/Templates/Daily note`

### E. TTS
```bash
# Edge needs no key — set voice via config if supported, else document tts.edge.voice
hermes config set tts.edge.voice '<voice>'   # when key exists
```
Fallback: ensure `config.yaml` `tts.edge.voice` is the approved voice.

### F. Daily briefing cron
Only if approved. `cronjob(action="list")` first. Example shape:

```python
cronjob(
  action="create",
  name="Daily Briefing",
  schedule="0 8 * * *",  # user-approved
  prompt="""You are running the user's scheduled daily briefing at the configured local time.
Produce a concise briefing with only these approved sections: <sections>.
Use configured integrations only when available. Use web search for weather/news only if approved.
If a section is unavailable, say so. No fabricated agenda. No memory writes. No credentials.
Deliver only the final briefing.""",
  enabled_toolsets=["web"],  # add more only if required and available
)
```

Self-contained prompt. No chat-context dependency. No Mnemosyne toolset.

### G. Optional Google
Load `google-workspace` skill. User completes OAuth in browser. Store client/token only under profile paths Hermes expects — never in the git distribution.

### H. Optional Telegram
User copies `.env.example` → `.env` and fills `TELEGRAM_*`. Enable platform via supported Hermes gateway setup. Do not paste tokens into chat.

### I. Optional config guard
If user wants drift protection on model keys:

```bash
# set expects to THEIR chosen provider/model
cronjob(
  action="create",
  name="donna-config-guard",
  schedule="every 15m",
  script="config_guard.py",  # relative to profile scripts/
  no_agent=True,
)
```

Ensure `DONNA_EXPECT_MODEL_PROVIDER` / `DONNA_EXPECT_MODEL_DEFAULT` are in the profile environment or pass `--expect` via a thin wrapper script the user owns. **Do not** hardcode upstream author models into the shipped guard defaults.

## Phase 4 — Verify checklist

- [ ] `hermes memory status` → mnemosyne active/available
- [ ] `MNEMOSYNE_DATA_DIR` points at profile path (confirm via path existence, not dumping .env)
- [ ] Vault has PARA + templates + `.obsidian`; `OBSIDIAN_VAULT_PATH` set
- [ ] Timezone readback matches request
- [ ] TTS voice set
- [ ] Briefing job listed with correct schedule (if requested)
- [ ] No secrets in SOUL/AGENTS/skills/cron prompts
- [ ] USER.md / MEMORY.md contain no API keys

Final report: Done / Verified / Gate (OAuth, Telegram token, gateway restart) / Blocker.

## Pitfalls

1. **Clone-vs-install:** `hermes profile install` copies distribution-owned files into `~/.hermes/profiles/donna/`. Ensure `scripts/` and `assets/` are listed in `distribution_owned` (they are in this package).
2. **Relative vault paths break file tools** — always absolute `OBSIDIAN_VAULT_PATH`.
3. **Daily folder nesting** — format `YYYY/MM/YYYY-MM-DD` requires month folders; create on first daily or let Obsidian/agent create them.
4. **Gateway restart** from inside gateway is blocked — instruct external restart only.
5. **Do not ship** `google_token.json`, Telegram tokens, or live `cron/jobs.json` with personal prompts.

## When user says “set me up like Donna”

Run this skill end-to-end. That is the product.
