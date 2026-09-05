# lu-zero-ops

## What

Host maintenance scripts and related cron on **lu-zero** (Maestro home). Same ops pattern as other fleet hosts.

## Paths (local on lu-zero)

| What | Where |
|------|--------|
| Scripts | `/root/scripts` |

## Typical scripts

| Script | Role |
|--------|------|
| `backup-withered-nexus.sh` | Backup helper (lu-zero copy may be backup/legacy; live WN is on **lu-one**) |
| `checkdiskspace.sh` | Disk space checks / Discord alerts |
| `checkjournal.sh` | Journal checks / alerts |
| `docker-prune-buildcache.sh` | Docker build-cache prune |
| `fix-lu-zero-default-ssl.sh` | SSL/default site helper |
| `ollama-tunnel.sh` | Ollama SSH tunnel helper |
| `include_amvara_bash_functions.sh` | Shared bash includes |

## Source of truth

Files under `/root/scripts` and root crontab / `/etc/cron.d` as applicable.

## Normal behavior

- Inspect before changing cron or alert webhooks.
- Never post webhook URLs or secrets to Discord.
- Minecraft **live** ops belong on **lu-one** (`lu-one-ops` / `withered-nexus`), not here.
