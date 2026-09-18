# Donna — Hermes executive-assistant profile

![Donna](assets/donna.png)

**Donna** is an open [Hermes Agent](https://hermes-agent.nousresearch.com/docs) **profile distribution**: persona, operating doctrine, full-stack onboarding, and a PARA Obsidian vault starter — packaged the same way as [ptah](https://github.com/Salt-555/ptah).

Install once, run guided setup, get a stack aligned with a production Donna profile:

| Layer | What you get |
|---|---|
| **Persona** | Sharp, discreet, outcome-focused EA (`SOUL.md`) — archetype, not TV role-play |
| **Doctrine** | Autonomy without pestering; verify before “done” (`AGENTS.md`) |
| **Memory** | Onboarding wires **Mnemosyne** profile-scoped (local SQLite), `auto_sleep: false` until you measure recall |
| **Notes** | Dedicated **Obsidian** vault: PARA + Daily + Inbox + templates + `.obsidian` |
| **Rhythm** | Optional daily briefing cron; optional config-drift guard |
| **Voice** | Edge TTS (no API key); voice chosen in onboarding |
| **Integrations** | Optional Telegram / Google Workspace — your keys, your OAuth |

**No credentials, sessions, personal memory, or model pins ship in this repo.**

## Requirements

- [Hermes Agent](https://hermes-agent.nousresearch.com/docs) `>= 0.14.0`
- A model provider already working (`hermes setup` / `hermes model`) or keys you add yourself
- Optional: Obsidian app (Flatpak/desktop/native) for the vault UI
- Optional: Mnemosyne plugin packages per current Hermes memory docs

## Install

```bash
hermes profile install github.com/unsulabs/donna --alias
```

`--alias` gives you a `donna` command. Without it: `hermes -p donna …`.

Then:

```bash
donna model          # or: hermes -p donna setup
donna chat           # first message: accept full setup when offered
```

Update later (keeps your `.env`, memories, sessions):

```bash
hermes profile update donna
```

### Local dev install

```bash
hermes profile install /path/to/this/checkout --name donna --alias
```

## First-run orientation (`donna-setup`)

On first chat, Donna offers setup. Say **yes** / **set me up** / **full setup**.

The **`donna-setup`** skill walks:

1. Identity + reply style  
2. Timezone + weather city + TTS voice  
3. **Mnemosyne** memory (profile data dir + host LLM)  
4. **Obsidian vault** scaffold (PARA) + `OBSIDIAN_VAULT_PATH`  
5. Optional daily briefing  
6. Optional Telegram / Google / config guard  
7. Toolset peel-back (everything useful starts on; you turn off what you do not want)

Nothing account-shaped happens without your approval. Secrets never go in chat — only `.env` and official OAuth/device flows.

### Vault scaffold (manual)

```bash
python3 scripts/scaffold_vault.py --vault ~/Documents/Donna-Vault
# then set OBSIDIAN_VAULT_PATH to that absolute path in the profile .env
```

`--dry-run` preview; `--force` overwrite starter files only.

## Layout

```text
donna/
├── distribution.yaml     # hermes profile install manifest
├── SOUL.md               # persona
├── AGENTS.md             # operating principles
├── config.yaml           # safe defaults (no model pin, no secrets)
├── profile.yaml
├── .env.example
├── memories/             # bootstrap templates only
├── skills/donna-setup/   # full-stack onboarding
├── scripts/
│   ├── scaffold_vault.py
│   └── config_guard.py   # optional drift guard (expects via env/flags)
├── assets/vault-starter/ # PARA + .obsidian + templates
└── skins/donna.yaml
```

Hermes still seeds its **bundled** skill library (Obsidian, Google Workspace, docs, GitHub, …) on the profile. This distribution adds Donna-specific doctrine + setup + vault.

## What is never included

- `.env`, `auth.json`, OAuth tokens, Google client secrets  
- Live `cron/jobs.json` with personal prompts  
- Mnemosyne databases, sessions, logs  
- Hardcoded provider/model identities of any one operator  

## Trust & safety

- Profile install is scoped to `~/.hermes/profiles/donna/` (or `--name`).  
- Broad tools (terminal, browser, files) are part of the default CLI surface — same as a fully configured assistant. Peel back in onboarding.  
- `approvals.mode: manual` and `approvals.cron_mode: deny` ship on.  
- `privacy.redact_pii: true`, `security.redact_secrets: true`.

## License

MIT — see [LICENSE](LICENSE).

## Credits

- Runtime: [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent)  
- Distribution pattern: [Salt-555/ptah](https://github.com/Salt-555/ptah)  
- Earlier Donna starter experiments: community `donna-starter` profiles  
