# amvara2-haproxy

## What

**HAProxy** edge proxy on **amvara2** (ports 80/443, `network_mode: host`, certs from `certs-ssl`). Distinct from catalog **`haproxy`** on **amvara3**.

## Paths (on amvara2)

| What | Where |
|------|--------|
| Project | `/home/amvara/projects/haproxy` |
| Compose | `docker-compose.yml` |
| Config | `conf/${HOSTNAME}.cfg` mounted into container |
| Certs | `/home/amvara/projects/certs-ssl` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'docker ps --filter name=haproxy; ls /home/amvara/projects/haproxy /home/amvara/projects/certs-ssl'
```

## Source of truth

`conf/`, compose, certs layout on amvara2.

## Normal behavior

- Proxy/TLS changes are high-impact: confirm before reload/redeploy.
- Never post private keys or full cert material to Discord.
- Backend apps are separate catalog entries (`amvara-de`, `gitlab`, `sentry`, …).
