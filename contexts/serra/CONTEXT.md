# Serra (shared pack)

## What

Laravel ecommerce (API + React). Three Docker environments on lu-zero share this pack.

## Environments (catalog ids)

| Catalog id | Path | Role |
|------------|------|------|
| `serra-prod` | `/srv/serra/prod` | Production |
| `serra-style` | `/srv/serra/style` | Style / design stack |
| `serra-stage` | `/srv/serra/stage` | Stage / pre-prod |

Compose project names: `serra-prod`, `serra-style` (stage may differ; check compose files under each path).

## Autoagents

| Catalog id | Dir (under env path) | Loop |
|------------|----------------------|------|
| `serra-prod` | `source/autoagents/` | `autoagents-loop.sh` |
| `serra-stage` | `source/autoagents/` | `autoagents-loop.sh` |
| `serra-style` | `source/agents/` | `laravel-ecommerce-agent-loop.sh` |

When Luipy asks for an agent task: write under that env's `tasks/` per local `TASKS-README.md`, check the loop is running, start/restart if needed. No confirmation wait unless asked to discuss first.

## Source of truth

Prefer the **active environment tree** (usually `source/` under the env path):

1. `AGENTS.md`
2. `.cursor/rules/` and `.cursor/skills/`
3. `docs/` when present

Maestro only keeps this short map. Do not duplicate Serra agent policy here.

## Normal behavior

- Confirm **which env** (prod / style / stage) before mutating.
- Prefer the smallest change; follow Serra git/agent branch rules from that tree.
- No secrets in Discord. Do not touch unrelated Docker projects.
