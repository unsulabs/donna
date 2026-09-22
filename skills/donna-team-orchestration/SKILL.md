---
name: donna-team-orchestration
description: Use when intake, multi-bot handoff, kanban assign, or long-running project tracking for Donna's team.
version: 1.1.0
author: Unsu Labs
license: MIT
metadata:
  hermes:
    tags: [donna, orchestration, kanban, bots, team, ea]
---

# Donna team orchestration

Load **before** assigning work to another profile or answering program-status questions that involve specialists.

## Source of truth

1. `$HERMES_HOME/.team` — roster, channels, dispatch checklist  
   (copy from distribution `.team.example` if missing)
2. `$HERMES_HOME/AGENTS.md` — hard rails  
3. Vault projects: `$OBSIDIAN_VAULT_PATH/Projects` (when set)  
4. Kanban board: `donna-ops` (or the board named in `.team`)

## Time 1 — Intake (always)

From a dump or new initiative:

1. Split into tasks: what | owner | status | horizon | blocker  
2. Owner ∈ {user, human, member from `.team`}  
3. Horizons: `continuous` | `month` | `quarter` | `no fixed date` — **no fake deadlines**  
4. Write/update vault project note + optional kanban cards in **triage/todo**  
5. Do **not** open with “I can write the site/copy for you”

## Time 2 — Execute / handoff

When the user says to work a stream:

1. `read_file` `.team` member block  
2. Read assignee `doctrine_paths` (minimum SOUL + pipeline skill head if any)  
3. If `.team` marks **bootstrapping** / blockers → report blocker; do not pretend dispatch succeeded  
4. Channel pick:  
   - **kanban** (default durable): `kanban_create` title + body brief + `assignee`  
   - Bot Chat / Desktop: `message_agent` only if this session is Bot Chat  
   - CLI: `hermes -p <name> chat -q '…'` for one-shot  
5. Record card id / command evidence in the vault project note  
6. Follow until card done/blocked; verify files/URLs; update inventory  
7. Closing a card ≠ closing a multi-month project

## Brief templates

### → content specialist

- Audience, channel, goal, tone, constraints  
- Source facts (links/paths) — no invented claims  
- Deliverable format + length  
- Success check (what Donna will verify)

### → build / engineering specialist

- Goal + non-goals  
- Repo / path (`dir:` or worktree)  
- Acceptance evidence (commands/tests)  
- Lane hint only if objective criteria known  
- Secrets: never paste; point to `.env` policy  
- After run: verify paths; distrust self-report alone

## Kanban quick CLI

```bash
hermes kanban --board donna-ops list
hermes kanban --board donna-ops create "Title" --assignee <profile> --body "…" --tenant <project-slug>
hermes kanban --board donna-ops show <id>
hermes kanban --board donna-ops comment <id> --body "…"
```

Prefer tools `kanban_*` when enabled in this session.

Optional board-wide terminal-event notify (no LLM):

```bash
# Set DONNA_KANBAN_BOARD_DB to the board sqlite path, then:
python3 scripts/kanban_board_notify.py
```

## Anti-patterns

- Pitching Donna capabilities instead of inventory  
- Assigning profiles not listed in `.team`  
- Using only `delegate_task` for multi-day specialist work  
- Marking a program “done” because one card closed  
- Wiping tasks when the user rejects a framing
