# haproxy

## What

**HAProxy** reverse-proxy stack on **amvara3** (Docker Compose), typically in front of services such as Redmine/Cometa-era routing.

## Paths (on amvara3)

| What | Where |
|------|--------|
| Project | `/home/gitlab-runner/haproxy` |
| Compose | `docker-compose.yml` |
| Config | `conf/` |
| Deploy helper | `deploy.sh` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara3 'docker compose -f /home/gitlab-runner/haproxy/docker-compose.yml ps; ls /home/gitlab-runner/haproxy'
```

## Source of truth

`README.md`, `conf/`, compose on amvara3.

## Normal behavior

- Proxy changes are high-impact: confirm before reload/redeploy.
- Never post TLS private keys or secrets to Discord.
- Redmine app → **`redmine`**. Aux DBs → **`amvara3-dbs`**.
