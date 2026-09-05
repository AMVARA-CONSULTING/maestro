# amvara9-ops

## What

Host maintenance on **amvara9** (disk, journal monitor, docker status, Satisfecho HTTP 500 probe). App work for the POS lives under catalog **`pos`**.

## Paths (on amvara9)

| What | Where |
|------|--------|
| Host scripts (catalog path) | `/root/scripts` |
| Amvara shared disk/journal | `/etc/misc/amvara/scripts` |
| Diskalert dir | `/root/diskalert` (often empty) |

## Typical scripts

| Location | Script | Role |
|----------|--------|------|
| `/root/scripts` | `check_docker_status.sh` | Docker status checks |
| `/root/scripts` | `check_satisfecho_500.sh` | Satisfecho 500 probe |
| `/root/scripts` | `report_journal_errors.sh` | Journal error reporting |
| `/root/scripts` | `checkDisk.sh` | Disk helper (legacy name) |
| `/etc/misc/amvara/scripts` | `checkdiskspace.sh` | Disk space / alerts |
| `/etc/misc/amvara/scripts` | `test-monitor-alert.sh` | Journal / Discord info alerts |
| `/etc/misc/amvara/scripts` | `include_amvara_bash_functions.sh` | Shared bash includes |

## Cron (root, indicative — host ops only)

| Schedule | Role |
|----------|------|
| Every ~15 min | `checkdiskspace.sh` from `/etc/misc/amvara/scripts` |
| 06 / 14 / 22 | `test-monitor-alert.sh info` |
| Every 5 min | `check_satisfecho_500.sh` |
| Every 30 min | `check_docker_status.sh` |

Do **not** treat app-specific jobs under `/development/pos` as part of this pack.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara9 'ls /root/scripts /etc/misc/amvara/scripts; crontab -l'
```

If direct SSH fails, hop via **amvara4** (see **`amvarabridge`** when that project is bound).

## Source of truth

`/root/scripts`, `/etc/misc/amvara/scripts`, and root crontab on amvara9.

## Normal behavior

- Inspect before changing cron or alert wiring.
- Never post webhook URLs, tokens, or secrets to Discord.
- POS application code/compose → catalog **`pos`**.
