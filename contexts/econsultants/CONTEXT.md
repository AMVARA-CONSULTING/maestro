# econsultants

## What

Static marketing / company site for **econsultants** (renewables / wind + rail) on **amvara2**. Spanish pages at repo root; English under `en/`. Live: https://econsultants.es · stage: https://econsultants.amvara.de.

Stack: pure HTML / CSS / JS (no SPA). Preview nginx via compose on `127.0.0.1:9089`. Issues on **GitLab** (`git.amvara.de/econsultants/econsultants`), not GitHub.

## Paths (on amvara2)

| What | Where |
|------|--------|
| Repo | `/home/amvara/projects/econsultants` |
| Compose / nginx preview | `docker-compose.yml`, `nginx/` |
| **Autoagents** | `agents/` · loop `agent-loop.sh` |
| Docs | `README.md`, `AGENTS.md`, `SERVING.md` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'ls /home/amvara/projects/econsultants; docker compose -f /home/amvara/projects/econsultants/docker-compose.yml ps'
```

## Source of truth

On amvara2: `AGENTS.md`, `agents/TASKS-README.md`, `SERVING.md`, project `.cursor/`.

## Normal behavior

- Static site only unless a task says otherwise; prefer shared `css/` / `js/` / `assets/`.
- **Autoagents:** tasks under `agents/tasks/`; GitLab via `glab` / project helpers. Verify/start `agent-loop.sh` when creating work.
- Edge routing → **`amvara2-haproxy`**. Host ops → **`amvara2-ops`**.
- Never post tokens / `.env` / `autoagents.env` to Discord.
