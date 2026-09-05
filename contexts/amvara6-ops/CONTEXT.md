# amvara6-ops

## What

Host maintenance on **amvara6** (disk checks and shared Amvara scripts). Separate from **`selenium-chrome`**.

## Paths (on amvara6)

| What | Where |
|------|--------|
| Scripts | `/home/amvara/projects/scripts` |

## Typical scripts

| Script | Role |
|--------|------|
| `checkdiskspace.sh` | Disk space checks / alerts |
| Other Amvara helpers | Same family as other `amvara*-ops` packs |

## Cron (indicative)

| Schedule | Role |
|----------|------|
| Every ~7 min | `checkdiskspace.sh -hn -nl` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara6 'ls /home/amvara/projects/scripts; crontab -l'
```

If direct SSH fails, hop via **amvara4** (`amvarabridge` practices when that project is bound).

## Normal behavior

- Inspect before changing cron.
- Never post secrets to Discord.
- Selenium container → **`selenium-chrome`**. Cognos and other stacks on this host are **out of catalog** unless Luipy adds them.
