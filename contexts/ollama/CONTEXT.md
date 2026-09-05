# ollama

## What

**Ollama** on **amvara8**: host systemd service providing local LLM models for the Amvara fleet (and related tools). Example consumer: **d-writer** on amvara4 (`qwen-3.6:27b-writer`).

## Paths (on amvara8)

| What | Where |
|------|--------|
| Model / data dir (catalog path) | `/data/ollama` |
| Systemd | `ollama.service` (`/usr/local/bin/ollama serve`) |
| Binary | `/usr/local/bin/ollama` |
| Related (optional trees) | `/root/ollama_ai`, `/development/ollama` — not the primary service |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara8 'systemctl status ollama.service --no-pager; ollama list'
```

## Source of truth

`ollama.service`, live `ollama list` / model storage under `/data/ollama`, any runbooks Luipy points to.

## Normal behavior

- Prefer status/list/read-only probes unless asked to pull/delete models or restart the service.
- Heavy GPU/RAM host: avoid unnecessary model pulls or full scans.
- Never post API keys or auth material to Discord.
- Do not edit **amvara.ai** from this pack; that is **`amvara-ai`**.
