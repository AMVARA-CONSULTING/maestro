# amvara-de

## What

Company website **amvara.de** on **amvara2** (Angular frontend + optional Python backend for PDF/contact). **Not** amvara.com (different property).

Containers typically: `amvara_prod` / `amvara_stage` (+ backends). Source tree used in catalog: `/root/work/amvara-2.0`.

## Paths (on amvara2)

| What | Where |
|------|--------|
| Source / compose | `/root/work/amvara-2.0` |
| Related under projects | `/home/amvara/projects/amvara` (may hold related trees) |
| **Autoagents** | `/root/work/amvara-2.0/autoagents/` · loop `autoagents-loop.sh` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'docker ps --filter name=amvara; ls /root/work/amvara-2.0; head -n 40 /root/work/amvara-2.0/README.md'
```

## Source of truth

`README.md`, compose files, `docs/`, project agent docs under that tree.

## Normal behavior

- Prefer smallest change; confirm prod vs stage before restart/redeploy.
- **Autoagents:** tasks under `autoagents/tasks/`; check/start `autoagents-loop.sh` for agent work.
- Never post secrets to Discord.
- Edge TLS/routing → **`amvara2-haproxy`**. Host ops → **`amvara2-ops`**.
