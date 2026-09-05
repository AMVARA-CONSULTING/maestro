# amvara3-ops

## What

Host maintenance on **amvara3** (disk, journal Discord alerts, renew, backups). Separate from Redmine / HAProxy / aux DBs.

## Paths (on amvara3)

| What | Where |
|------|--------|
| Scripts | `/home/amvara/projects/scripts` |
| Mirror | `/etc/misc` (often same script set) |

## Typical scripts

| Script | Role |
|--------|------|
| `checkdiskspace.sh` | Disk space checks |
| `test-monitor-alert.sh` | Journal / Discord info alerts |
| `renew.sh` / `renew_certbot_certs.sh` | Cert renew |
| `backup.sh` / `backup_etc.sh` | Backup helpers |

## Cron (indicative)

| Schedule | Role |
|----------|------|
| Every ~7 min | `checkdiskspace.sh` |
| Every 8h | `test-monitor-alert.sh info` |
| Daily | cert renew, etc backup; Redmine `./backup.sh` lives under **`redmine`** tree |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara3 'ls /home/amvara/projects/scripts; crontab -l'
```

## Normal behavior

- Inspect before changing cron/alerts.
- Never post secrets to Discord.
- Apps: **`redmine`**, **`haproxy`**, **`amvara3-dbs`**.
