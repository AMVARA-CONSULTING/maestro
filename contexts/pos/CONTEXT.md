# pos

## What

**Satisfecho** restaurant POS on **amvara9**: Angular frontend, FastAPI backend, PostgreSQL, Redis, HAProxy (Docker Compose).

Host: typically **satisfecho.de** (SSH alias `amvara9`).

## Paths (on amvara9)

| What | Where |
|------|--------|
| Repo / deploy | `/development/pos` |
| Compose | `docker-compose.yml` + `docker-compose.prod.yml` (project `pos`) |
| Front / back | `front/`, `back/` |
| **Autoagents** | `/development/pos/agents/` · loop `pos-cursor-loop.sh` (ignore `zz_cursor-agents-do-not-use/`) |

Other trees under `/development/` (barber, numbered restaurant forks, `pos-contracts`, `pos-marketing`, glueproject) are **out of this catalog** unless Luipy adds them.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara9 'docker compose -f /development/pos/docker-compose.yml -f /development/pos/docker-compose.prod.yml ps; ls /development/pos'
```

## Source of truth

On amvara9: `README.md`, `docs/`, compose files, project `.cursor/` / agent docs if present.

## Normal behavior

- Prefer smallest change; confirm compose project `pos` before restart/redeploy.
- **Autoagents:** tasks under `agents/tasks/`; health = `pos-cursor-loop.sh` process.
- Host disk/journal/docker probes → **`amvara9-ops`**, not this pack.
- Never post `.env`, DB passwords, or tokens to Discord.
