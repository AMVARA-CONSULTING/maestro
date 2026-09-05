# stunnel-redmine

## What

**Stunnel Redmine client** on **amvara2**: TLS tunnel **amvara2 → amvara3** for Redmine. Local Redmine Docker on amvara2 is **disabled** (containers exited; compose marked DISABLED). Live Redmine app catalog entry is on **amvara3** (`redmine`).

## Paths (on amvara2)

| What | Where |
|------|--------|
| Project / unit copy | `/home/amvara/projects/stunnel-redmine` |
| Systemd | `stunnel-redmine.service` |
| Config | `/etc/stunnel/redmine-client.conf` (do not paste secrets to Discord) |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'systemctl status stunnel-redmine.service --no-pager; ls /home/amvara/projects/stunnel-redmine'
```

## Source of truth

stunnel unit + `redmine-client.conf`, project files under `stunnel-redmine/`. App/data for Redmine → amvara3 **`redmine`**.

## Normal behavior

- Prefer status/connectivity checks unless asked to change stunnel config or restart the unit.
- Do not “bring back” local amvara2 Redmine containers unless Luipy explicitly asks.
- Never post stunnel/certs/keys to Discord.
- Host disk/cron → **`amvara2-ops`**.
