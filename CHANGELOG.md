# Changelog

## 2.0.0-rc.1 · integración y verificación · 2026-09-25

- Merged into `main` as `728aebe90418b8909e1406f878fa0a78bb1156e4` (PR #1 from
  `feat/donna-2.0.0-rc1` @ `5a0d8630`).
- Remote CI observed green on 2026-09-23 in three runs — `35825804078` (push),
  `35825817189` (pull_request), `35826010874` (push, `main`) — across Python
  3.10, 3.11, 3.12 and 3.13.
- Fresh install from the public URL verified on 2026-09-25 in a staging profile:
  `hermes profile install github.com/unsulabs/donna` printed
  `✓ Installed 'donna-gh-verify' v2.0.0-rc.1`, exit 0.
- Deterministic core exercised on that fresh install: `init --apply` (wrote
  `donna-ops.json`, mode 600; its declared board was then pointed at an existing
  board, so no byte size is quoted — the size varies with the board), `doctor`
  (`ok: true`), `doctor --native` (`ok: true`), `plan-import examples/plan.json`,
  `activate`, `render` (6 projected Markdown files), `review`, `status`.
- Observed limit: `doctor --native` returns exit 3 / `native.ok: false` when the
  declared board does not exist. A missing board is a diagnosis, not a defect.
- NOT claimed as passed: live gates L01–L18 (`docs/ACCEPTANCE.md`) — real channel,
  model, gateway/dispatcher topology and Obsidian UI on an authorized staging.

## 2.0.0-rc.1 · 2026-09-22

Candidate based on `ef15483af9765c32e7f86e2091a7709bbd387bb9` (1.1.0).

- Whole-life mission, six operational skills and explicit per-session bootstrap.
- Stdlib coordination journal: planning, roles, dependencies, human capacity,
  attested readiness, approvals, idempotent durable dispatch and bounded recovery.
- Native delivery is separate from semantic acceptance; remediation preserves
  card history, invalidates downstream acceptance and has a finite budget.
- Existing-vault Markdown/Kanban projection with stable IDs, editable project
  fields, conflict preservation, backups and explicit resolution.
- Bounded native cron preflight with review leases, reconciliation and post-work
  acknowledgement. Native scheduler/dispatcher retained; no second daemon.
- Explicit staged migration, offline tests, subprocess contract fixtures,
  acceptance scenarios and implementation handoff.
- BREAKING: `.team` v2 is strict JSON, not v1 freeform YAML. Do not overwrite the
  live roster. Migrate deliberately and reverify readiness.
- BREAKING: legacy board notifier exits with a migration notice; pause its old
  no_agent cron before update and install the skill-backed review in staging.
- Fresh defaults remove broad script-execution approval bypasses. Live config,
  providers, secrets and existing tool policies must be merged, not overwritten.
- No claim that offline tests validate live Hermes, models, accounts or Obsidian UI.

## 1.1.0 · 2026-09-22

Baseline introduced orchestrator doctrine, `.team.example`, team-orchestration
skill and optional board notification. Original history remains in Git.

## 1.0.0 · 2026-09-18

Initial public profile distribution with persona, setup and vault starter.
