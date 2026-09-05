# amvara10-ops

## What

Host maintenance scripts and cron on **amvara10** (disk / journal monitor). Separate from app trees under `/opt/km0-*` and `/opt/opencloud`.

## Paths (on amvara10)

| What | Where |
|------|--------|
| Scripts (cron) | `/opt/amvara/scripts` |
| Diskalert dir | `/root/diskalert` (often empty; live scripts are under `/opt/amvara/scripts`) |
| Related | `/opt/amvara/sunday-updates` (catalog **`sunday-updates`**, not this pack) |

## Typical scripts

| Script | Role |
|--------|------|
| `checkdiskspace.sh` | Disk space checks / alerts |
| `test-monitor-alert.sh` | Journal / monitor Discord info alerts |
| `include_amvara_bash_functions.sh` | Shared bash includes |

## Cron (root, indicative)

| Schedule | Role |
|----------|------|
| Every ~15 min | `checkdiskspace.sh` (flock) |
| Every 8h | `test-monitor-alert.sh info` (flock) |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara10 'ls /opt/amvara/scripts; crontab -l'
```

If direct SSH fails, hop via **amvara4** (see catalog **`amvarabridge`** when that project is bound).

## Source of truth

Files under `/opt/amvara/scripts` and root crontab on amvara10.

## Normal behavior

- Inspect before changing cron or alert wiring.
- Never post webhook URLs, tokens, or secrets to Discord.
