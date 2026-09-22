# Changelog

## 1.1.0 — 2026-09-22

- **Orchestrator rails:** EA intake-first doctrine, long-running projects, bots = profiles (aligned with production Donna behavior; public/generic wording)
- **`.team.example`:** authoritative multi-bot roster template (copy to live `.team`; no secrets/paths of a specific operator)
- **Skill `donna-team-orchestration`:** Time 1 intake / Time 2 handoff, brief templates, kanban CLI, anti-patterns
- **`scripts/kanban_board_notify.py`:** optional board-wide terminal-event notify via env (`DONNA_KANBAN_BOARD_DB`, …)
- **`donna-setup`:** optional team roster + `donna-ops` board + board notify steps
- **`profile.yaml`:** Bot Mode `ui_meta.hermes-bots` title; orchestrator description
- **`config.yaml`:** kanban toolset on telegram surface; dispatcher comments; still no model pins
- **README / MEMORY / USER templates:** orchestration status language and stack fields
- **distribution.yaml:** v1.1.0; own `.team.example` + new skill/script

## 1.0.0

- Initial public distribution for `hermes profile install github.com/unsulabs/donna`
- Donna persona (`SOUL.md`) + operating doctrine (`AGENTS.md`)
- Full-stack onboarding skill `donna-setup` (Mnemosyne, PARA vault, briefing, TTS, optional integrations)
- `assets/vault-starter` + `scripts/scaffold_vault.py`
- Optional `scripts/config_guard.py` (no hardcoded provider/model)
- Clean `config.yaml` defaults without credentials or model pins
