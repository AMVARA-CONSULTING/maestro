# mc-web (mc.ldeluipy.es on lu-one)

## What

Public Minecraft website for the community (`mc.ldeluipy.es`), served by Apache on **lu-one**.

## Paths (on lu-one)

| What | Where |
|------|--------|
| Docroot | `/var/www/mc.ldeluipy.es` |
| Apache site | `/etc/apache2/sites-enabled/mc.ldeluipy.es.conf` |
| **Autoagents** | `/var/www/mc.ldeluipy.es/agents/` · loop `agent-loop.sh` |

## How to reach from Maestro (lu-zero)

```bash
ssh lu-one 'ls /var/www/mc.ldeluipy.es | head'
```

## Source of truth

Docroot (`AGENTS.md`, `frontend/`, `admin/`, etc.) on lu-one. Prefer project docs there over inventing layout.

## Normal behavior

- Web/static/PHP changes only unless asked otherwise.
- **Autoagents:** tasks under `agents/tasks/`; verify `agent-loop.sh` when creating agent work.
- Not the Paper server itself (see `withered-nexus`).
