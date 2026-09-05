# sentry

## What

**Sentry** error-tracking stack on **amvara2** (Docker Compose): web, worker, cron, redis, postgres.

## Paths (on amvara2)

| What | Where |
|------|--------|
| Project | `/home/amvara/projects/sentry` |
| Compose | `docker-compose.yml` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'docker ps --filter name=sentry; docker compose -f /home/amvara/projects/sentry/docker-compose.yml ps'
```

## Source of truth

Compose and project files under `/home/amvara/projects/sentry`.

## Normal behavior

- Prefer status/logs unless asked to upgrade/restart.
- Never post Sentry keys, DB passwords, or `.env` to Discord.
- Edge routing → **`amvara2-haproxy`**. Host ops → **`amvara2-ops`**.
