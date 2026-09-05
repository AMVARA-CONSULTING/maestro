# amvara2-ops

## What

Host maintenance on **amvara2** (disk, journal Discord alerts, certbot, gitlab version check, backups). Separate from app packs and from **`stunnel-redmine`**.

## Paths (on amvara2)

| What | Where |
|------|--------|
| Scripts | `/home/amvara/projects/scripts` |
| Also used by cron | `/etc/misc` (often same / linked script set) |

## Typical scripts

| Script | Role |
|--------|------|
| `checkdiskspace.sh` | Disk space checks |
| `test-monitor-alert.sh` | Journal / Discord info alerts |
| `renew_certbot_certs.sh` | Cert renew |
| `gitlab_version_check.sh` | GitLab version probe (weekly) |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'ls /home/amvara/projects/scripts; crontab -l'
```

SSH: prefer Host `amvara2` (port **60022**). If direct fails → hop via **amvara4**.

## Normal behavior

- Inspect before changing cron/alerts.
- Never post secrets to Discord.
- Stunnel Redmine client → **`stunnel-redmine`**. Site → **`amvara-de`**. GitLab → **`gitlab`**. Edge proxy → **`amvara2-haproxy`**. Sentry → **`sentry`**.
