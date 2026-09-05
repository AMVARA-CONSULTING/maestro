# lu-one-ops

## What

Host maintenance scripts and cron on **lu-one** (typical ops pack pattern for every Maestro host).

## Paths (on lu-one)

| What | Where |
|------|--------|
| Scripts | `/root/scripts` |
| Migration notes | `/root/migration/` (docs only) |

## Cron (root)

| Schedule | Script |
|----------|--------|
| Daily ~05:15 | `backup-withered-nexus.sh` |
| Monthly restore-test | `restore-test-withered-nexus.sh` |
| Hourly | `checkdiskspace.sh` → Discord `#lu-one` |
| Every 6h | `checkjournal.sh` → Discord |
| Weekly | `docker-prune-buildcache.sh` |

## How to reach from Maestro (lu-zero)

```bash
ssh lu-one 'ls /root/scripts; crontab -l'
```

## Source of truth

Scripts under `/root/scripts` on lu-one; webhook/channel notes in `/root/migration/DISCORD-WEBHOOK.txt`.

## Normal behavior

- Prefer read-only inspection of cron/logs unless asked to change schedules or scripts.
- Never paste webhook URLs or secrets into Discord.
