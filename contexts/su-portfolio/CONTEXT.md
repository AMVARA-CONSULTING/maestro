# su-portfolio

## What

**Next.js** portfolio app on **amvara4**, deployed with Docker Compose (app + Caddy).

## Paths (on amvara4)

| What | Where |
|------|--------|
| Deploy root | `/srv/su-portfolio` |
| Source | `/srv/su-portfolio/source` |
| Compose | `docker-compose.prod.yml` |
| Caddy | `Caddyfile` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara4 'docker compose -f /srv/su-portfolio/docker-compose.prod.yml ps; ls /srv/su-portfolio/source'
```

## Source of truth

On the amvara4 tree: `source/README.md`, `source/AGENTS.md`, deploy compose files, project `.cursor/` if present.

## Normal behavior

- Prefer smallest change; confirm compose project before restart/redeploy.
- Do not confuse with other portfolio trees (e.g. Oracle `portfolio-mc`).
- Never post secrets to Discord.
