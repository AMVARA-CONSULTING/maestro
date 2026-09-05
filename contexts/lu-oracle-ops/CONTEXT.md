# lu-oracle-ops

## What

Host maintenance map for **lu-oracle** (Oracle Cloud VM, hostname `ldeluipy`). Catalog is **ops-only** on purpose: enough to reach the box for maintenance without listing every vhost/app.

## Host facts

| What | Value |
|------|--------|
| SSH (from lu-zero) | `ssh lu-oracle` |
| SSH user | `ubuntu` |
| Typical RAM | ~1 GiB (tight; avoid heavy builds/scans) |
| Disk | ~45 GiB root |
| Web stack | Apache2 + MariaDB (native; Docker usually idle) |
| Docroots | `/var/www/*.ldeluipy.es` and `/var/www/ldeluipy.es` |
| Code repos (not catalogued) | `/home/ubuntu/Repo/` |

## Paths (on lu-oracle)

| What | Where |
|------|--------|
| Scripts | `/home/ubuntu/scripts` |
| Home / notes | `/home/ubuntu` |
| Apache sites-enabled | `/etc/apache2/sites-enabled` |
| Optional vhost notes | `/home/ubuntu/APACHE_VHOSTS.md` |

## Typical scripts

| Script | Role |
|--------|------|
| `checkdiskspace.sh` | Disk space checks / alerts |
| `deploy.sh` / `deploy2.sh` | Deploy helpers |
| `fix-lu-zero-default-ssl.sh` | SSL helper (name is historical; runs in this tree) |
| `include_amvara_bash_functions.sh` | Shared bash includes |

## How to reach from Maestro (lu-zero)

```bash
ssh lu-oracle 'ls ~/scripts; free -h; df -h /; systemctl is-active apache2 mariadb'
```

Prefer light, read-only checks first. Do not start heavy Docker builds or full-tree scans unless asked.

## Source of truth

Scripts under `/home/ubuntu/scripts` on lu-oracle; Apache vhosts and `/var/www` for site-level work when the operator names a host/path.

## Normal behavior

- Maintenance and inspection only unless the operator asks to change something.
- Never paste secrets, `.env`, keys, or webhook URLs to Discord.
- Do not invent catalog apps for this host; add projects only when Luipy asks.
- This host is not Serra. Serra lives on **lu-zero** only (`serra-prod` / `serra-style` / `serra-stage`).
