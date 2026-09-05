---
name: autoagents
description: >-
  Create and supervise autoagents (agents) task queues for catalog projects that
  have the autoagents flag. Use when Luipy asks for NEW/FEAT tasks, to check if
  the agent loop is running, or to start/restart stuck loops.
---

# Autoagents (agents)

## What it is

Per-project adaptation of `/root/Repos/autoagents`: a bash **loop** (`autoagents-loop.sh`, `agent-loop.sh`, or a project-specific `*-loop.sh`) that cycles cursor-agent roles over markdown tasks under `<aa_dir>/tasks/`.

Canonical pipeline (see that install's `TASKS-README.md`):

`NEW-/FEAT-` → `WIP-` → `UNTESTED-` → `TESTING-` → `CLOSED-` → `done/YYYY/MM/DD/`

Base template lives at `/root/Repos/autoagents` (`IFNEWMUST.md`). **Each install differs** (dir name `agents/` vs `autoagents/`, loop filename, prompts). Always read the **project** tree on the catalog host.

## Catalog

Projects with autoagents have:

```json
"autoagents": { "enabled": true, "rel_dir": "…", "loop": "…" }
```

relative to the catalog `path`. `/list_projects` marks them **autoagents**. Session context injects dir + loop when bound.

## Workflow (normal)

1. Operator asks for a new task on project X (or health of agents).
2. Confirm catalog entry has `autoagents`. If not, say so (do not invent).
3. **Create task** under `<project>/<rel_dir>/tasks/` following **that** `TASKS-README.md` (usually `NEW-0-YYYYMMDD-HHMM-slug.md` for operator asks without a GitHub issue; use `FEAT-<n>-…` when tied to an issue). Sync integration branch first if the project requires it (`scripts/git-sync-*.sh`).
4. **Do not wait for confirmation** unless the operator asked to discuss first.
5. **Health:** "up" means a live process running the loop script (often `nohup`/`bash`, not always systemd). Check e.g. `pgrep -af '<loop-name>'`, recent `.runtime/loop.log` or `var/loop/loop.out`, stamps under `001-*/time-of-last-review.txt`.
6. If down or stuck: start from **repo root** (parent of the aa dir) with nohup/logging as that project already does; or kill + restart if Luipy asked / clearly hung. Prefer the project's existing run pattern.
7. Notify Luipy: task path created + loop status.

## Rules

- Never post secrets from `autoagents.env` / `.env` to Discord.
- Do not confuse **`autoagents-mcd.service`** on lu-zero (MCD web UI) with an agent loop.
- Do not treat `/data/amvara.ai/agents` as autoagents (different Python agents).
- Remote hosts: operate via `ssh <alias>` against paths on that host.
