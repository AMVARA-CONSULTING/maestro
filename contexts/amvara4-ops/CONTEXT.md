# amvara4-ops

## What

Host maintenance scripts and cron on **amvara4** (disk / journal monitor). Separate from **amvarabridge** (fleet bridge + auditor agent).

## Paths (on amvara4)

| What | Where |
|------|--------|
| Scripts (cron cwd) | `/etc/misc` |
| Diskalert dir | `/root/diskalert` (may be empty; live scripts are under `/etc/misc`) |

## Typical scripts

| Script | Role |
|--------|------|
| `checkdiskspace.sh` | Disk space checks / alerts |
| `test-monitor-alert.sh` | Journal / monitor Discord info alerts |
| `include_amvara_bash_functions.sh` | Shared bash includes |
| `crontab_mail.py` | Mail helper for cron |

## Cron (root, indicative)

| Schedule | Role |
|----------|------|
| Every ~6 min | `checkdiskspace.sh -hn` from `/etc/misc` |
| Every 8h | `test-monitor-alert.sh info` (flock) |
| 06:15 daily | amvarabridge `run-daily-audit.sh` (bridge project, not this pack) |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara4 'ls /etc/misc; crontab -l'
```

## Source of truth

Files under `/etc/misc` and root crontab on amvara4.

## Normal behavior

- Inspect before changing cron or alert wiring.
- Never post webhook URLs, tokens, or secrets to Discord.
- Fleet SSH / Ultron notify / auditor agent policy → catalog **`amvarabridge`**, not this pack.
