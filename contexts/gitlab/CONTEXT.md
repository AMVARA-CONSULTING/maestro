# gitlab

## What

**GitLab CE** on **amvara2** (Docker): `gitlab_node_new` plus Postgres/Redis sidecars.

## Paths (on amvara2)

| What | Where |
|------|--------|
| Project | `/home/amvara/projects/gitlab` |
| Compose | `docker-compose.yml` (and dated backups `docker-compose.yml_*`) |
| Config / data | under project `config/`, `docker/`, as laid out on disk |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'docker ps --filter name=gitlab; docker compose -f /home/amvara/projects/gitlab/docker-compose.yml ps'
```

## Source of truth

Compose + GitLab data/config on amvara2; prefer inspect before upgrades.

## Normal behavior

- GitLab upgrades/restarts are high-impact: confirm with Luipy first.
- Never post secrets, tokens, or backup paths with credentials to Discord.
- Version-check cron script lives under **`amvara2-ops`** scripts.
- HAProxy edge → **`amvara2-haproxy`**.
