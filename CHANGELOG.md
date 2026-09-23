# Changelog

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
