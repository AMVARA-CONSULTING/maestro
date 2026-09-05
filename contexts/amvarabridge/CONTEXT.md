# amvarabridge

## What

**Amvara SSH bridge** on **amvara4**: how to reach AmvaraN, journal auditor, side quests, and how to report/notify (including Discord as Ultron). Maestro uses this pack only when the session is **bound** to `amvarabridge`.

## Paths (on amvara4)

| What | Where |
|------|--------|
| Project root | `/root/amvarabridge` |
| Fleet list | `etc/hosts.list` |
| Env (secrets) | `etc/auditor.env` (mode 600 — never echo/commit) |
| Scripts | `scripts/` (`collect-journals.sh`, `run-daily-audit.sh`, `run-sidequest.sh`, `notify.sh`, …) |
| Prompts | `prompts/` |
| Quests | `quests/` |
| Cursor rules | `.cursor/rules/` (esp. `amvara-bridge.mdc`) |
| Run artifacts | `var/runs/`, `var/quests/` |

## Fleet (auditor / sidequests)

In scope: `amvara2`, `amvara3`, `amvara4`, `amvara6`, `amvara8`, `amvara9`, `amvara10`.  
Out of scope here: `amvara5` (down), `here`, and inventing other hosts. Do **not** catalog other Amvara boxes unless Luipy asks.

## SSH practices (from bridge rules)

- Prefer Host aliases from `~/.ssh/config` (`IdentitiesOnly` / keys as on the bridge host).
- On amvara4 itself: run local commands; for AmvaraN: `ssh -n -o BatchMode=yes -o ConnectTimeout=15 amvaraN '…'`.
- Prefer read-only probes unless the operator asks to change something.
- Journal **collection** is scripts-only; agents analyze run dirs and do not redefine the filter.

## Maestro hop / fallback (AmvaraN only)

When working Amvara fleet from Maestro (**lu-zero**):

1. Prefer **direct**: `lu-zero` → `ssh amvaraN '…'`.
2. If that connection fails: **fallback** `lu-zero` → `ssh amvara4` → from there `ssh amvaraN '…'` (or run the bridge scripts on amvara4).

Do not apply this hop pattern to non-Amvara hosts unless Luipy asks.

## Ultron feedback / notify

Scope feedback and ops notifications for bridge work go through bridge helpers (e.g. `scripts/notify.sh`: AutoMail + Discord as Ultron). Channel/token live in `auditor.env` — **never** paste to Discord. Prefer the project rules/skills on amvara4 over inventing a notify path.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara4 'ls /root/amvarabridge; head -n 30 /root/amvarabridge/.cursor/rules/amvara-bridge.mdc'
```

## Source of truth

On amvara4: `.cursor/rules/`, `prompts/`, `scripts/`, `quests/`, `etc/hosts.list`. This CONTEXT is only a minimum map.

## Normal behavior

- Bound sessions: follow bridge rules; smallest change; no secrets on Discord.
- Host disk/cron scripts alone → **`amvara4-ops`**. Ultron app code/service → **`ultron`**.
