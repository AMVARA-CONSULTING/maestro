# Maestro

Discord bot that runs slash commands and natural-language ops through cursor-agent.

Admin-only. Resolves work via a multi-host project catalog and short context packs.

## Layout

| Path | Role |
|------|------|
| `maestro/` | Bot runtime |
| `catalog/hosts/` | Project index (JSON) |
| `contexts/` | Per-project `CONTEXT.md` packs |
| `prompts/` | Agent / NL router prompts |
| `.cursor/` | Rules and skills |
| `systemd/maestro.service` | Service unit |
| `.env.example` | Secret keys (copy to `.env`) |

## Commands

| Command | What |
|---------|------|
| `/help` | Short guide |
| `/ping` | Latency check |
| `/list_projects` `[host]` | Catalogued projects |
| `/ca` | One-shot cursor-agent |
| `/ca_persist` | Thread + resumable Cursor chat |
| `/stop_ca` | Stop this thread's run + clear its queue |
| `/thread_end` | Close session and delete the thread |
| `/restart_maestro` | Restart the bot (admin only) |
| `@Maestro` / reply | Natural language → usually `ca_persist` |

## Setup

1. Copy `.env.example` → `.env` and fill Discord (and optional Redmine / OpenCloud) values.
2. Adjust `config.json` (guild / channel / homes / allowed admin user).
3. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
4. Install and enable `systemd/maestro.service` (edit paths if needed).
5. Restart with Discord `/restart_maestro` (or host CLI `python -m maestro.restart_guard operator` when not in an agent session).

## Notes

- Never commit `.env`, `data/`, or `.venv/`.
- Agents must not restart the service; only the admin does.
- Do not post secrets to Discord. Do not wipe end-user data without a scoped admin confirmation.
