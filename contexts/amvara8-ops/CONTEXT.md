# amvara8-ops

## What

Host maintenance scripts and cron on **amvara8** (disk, journal Discord alerts, housekeeping, cert renew, helpers). Separate from **`ollama`**, **`amvara-ai`**, and **`amvara8-vpn`**.

## Paths (on amvara8)

| What | Where |
|------|--------|
| Scripts | `/home/amvara/projects/scripts` |
| VPN client/gen helpers | `vpn/`, `generate_openvpn_client.sh`, `generate_client_certificate.sh` (VPN **services/configs** → **`amvara8-vpn`**) |

## Typical scripts

| Script | Role |
|--------|------|
| `checkdiskspace.sh` | Disk space checks / alerts |
| `test-monitor-alert.sh` | Journal / Discord info alerts |
| `housekeeping.sh` | Daily housekeeping |
| `renew.sh` | Cert / renew helper |
| `check_backup.sh` / `backup.sh` | Backup helpers |

## Cron (root, indicative — host ops)

| Schedule | Role |
|----------|------|
| Every ~7 min | `checkdiskspace.sh -hn -nl` |
| Every 8h | `test-monitor-alert.sh info` |
| Daily / weekly | housekeeping, renew, docker prune, etc. |

App-specific crons (Cometa cleanup, Ollama restart/watchdog) belong with those apps, not this pack’s focus unless Luipy asks.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara8 'ls /home/amvara/projects/scripts; crontab -l'
```

Fallback: via **amvara4** / **`amvarabridge`** if direct SSH fails.

## Source of truth

`/home/amvara/projects/scripts` and root crontab on amvara8.

## Normal behavior

- Inspect before changing cron or alert wiring.
- Never post secrets, keys, or webhook URLs to Discord.
- Ollama → **`ollama`**. amvara.ai → **`amvara-ai`** (read-only by default). OpenVPN/WireGuard → **`amvara8-vpn`**.
