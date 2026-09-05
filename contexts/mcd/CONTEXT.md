# MCD (Master Control Dashboard)

## What

Dashboard/overview for lu-zero projects (`master-control.py`, web UI).

## Paths

| What | Where |
|------|--------|
| App | `/var/www/mcd.lu-zero.ldeluipy.es` |
| Systemd | `autoagents-mcd.service` (**name only** — this runs the MCD web UI `master-control.py`, **not** an agent task loop) |

## Source of truth

`README.md`, `INSTALL.md`, `projects.json` in the app directory.

## Normal behavior

- Prefer read-only inspection unless asked to change MCD config or service state.
- Do **not** treat this as catalog autoagents. Real agent loops live on other projects (`autoagents` flag in catalog).
