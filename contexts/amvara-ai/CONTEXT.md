# amvara-ai

## What

**My.ai / amvara.ai** on **amvara8**: multi-user Discord co-pilot (Nemotron + tools) for Redmine / GitLab / SSH workflows. Compose project `amvaraai` under `/data/amvara.ai`.

## Paths (on amvara8)

| What | Where |
|------|--------|
| Deploy / repo | `/data/amvara.ai` |
| Compose | `docker-compose.yml` |
| Front / back / agents | `frontend/`, `backend/`, `agents/` |
| Docs | `docs/`, `README.md` |

## HARD RULE — no edits by default (Maestro)

**Inspect-only** for this project unless Luipy **explicitly** orders a concrete change (file, restart, deploy, etc.).

- Do **not** “improve”, refactor, reformat, or drive-by edit.
- Do **not** restart/redeploy containers unless explicitly asked.
- Read logs, `docker compose ps`, README/docs — that is fine.
- If a request is ambiguous about mutation → **ask first**, do not change.

This rule is stricter than the usual “smallest change” policy on purpose.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara8 'docker compose -f /data/amvara.ai/docker-compose.yml ps; ls /data/amvara.ai'
```

## Source of truth

On amvara8: `README.md`, `docs/`, compose and app trees. Prefer those over inventing behaviour.

## Normal behavior

- Default: report / explain only.
- Secrets (`.env`, tokens) never to Discord.
- Ollama models/service → catalog **`ollama`**, not this pack.
