# redmine

## What

**Redmine** app on **amvara3** (PurpleMine). Public URL `https://redmine.amvara.de` reaches it via **stunnel** (client on amvara2 → server on amvara3). Local Docker Redmine on amvara2 is disabled.

## Paths (on amvara3)

| What | Where |
|------|--------|
| Compose / project | `/home/amvara/projects/redmine` |
| Stunnel TLS helper | `stunnel-redmine.service` → `/etc/stunnel/redmine-server.conf` |
| Related under projects | `/home/amvara/projects/stunnel-redmine` |
| Data | `/home/data/redmine/{postgres,files,redmine,backups}` |

## MaestroBot

| What | Value |
|------|--------|
| Login | `MaestroBot` (user id `86`) |
| Catalog field | `redmine_doc_issue_id` on each project (maestro hub = `#8066`; opencloud = `#7530`; KM0 fallback = `#7594`; orphan L&F = `#8077`) |
| Secrets | Maestro host `/root/bots/maestro/.env` (`REDMINE_URL`, `REDMINE_API_KEY`, …) |
| How to post | Skill `redmine-notes` (ASD-STE100 English + Textile `{{collapse(Title · Project · cursor-stamp)}}`; stamp = first 8 hex chars of Cursor chat id) |
| Auto close | `/thread_end` posts **one** close note: catalog hub (or KM0 `#7594`) → else one primary mentioned work ticket → else `#8077`. Never fan-out. Skip with `clean:True`. |

Same project access pattern as Ultron (group **Amvara Developers** + **Desarrollador**). Never post API keys to Discord.

## Lookup policy (API vs SQL)

Exam 2026-09-02 (same 3 questions): SQL on `redmine_postgres` was **faster** (~0.4s on host, ~0.8s via SSH from lu-zero) than multi-call REST search (~1.3s). SQL `ILIKE` was also **more precise** for exact subject matches (API ranking missed `#7778` for “Fix MIF_CONS Reports”).

| Need | Prefer | Why |
|------|--------|-----|
| Create / update notes, read one issue | **API** (MaestroBot) | Safe default; no DB access; Ultron-compatible |
| Fuzzy / ranked search, normal ops | **API** `/search.json` | Enough most of the time |
| Exact substring in subject/description/journals; search looks wrong | **SQL read-only** on amvara3 | Faster + more reliable for forensic lookup |

SQL rules (hard):

1. **SELECT only.** Never `UPDATE` / `DELETE` / `INSERT` / `DROP` / schema changes via ad-hoc SQL.
2. Path: `ssh amvara3` → `docker exec -i redmine_postgres` → `psql` with container `POSTGRES_*` env (do not print passwords to Discord).
3. Prefer API for MaestroBot **writes** always.

## Access note

Host may expose `:3000` behind cloud firewall; README suggests SSH tunnel for laptop testing. Prefer project README / public URL over inventing hosts.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara3 'docker compose -f /home/amvara/projects/redmine/docker-compose.yml ps; systemctl status stunnel-redmine.service --no-pager'
# Read-only search example (no password echo):
# ssh amvara3 'docker exec -i redmine_postgres bash -lc '\''export PGPASSWORD="$POSTGRES_PASSWORD"; psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'\'''
```

## Source of truth

`README.md`, compose, stunnel unit/config on amvara3. Ultron API client reference on amvara4: `/root/Repos/ultron-redmine/ultron/redmine.py`.

## Normal behavior

- Prefer smallest change; confirm before compose/stunnel restart.
- Never post DB passwords or `.env` / API keys to Discord.
- HAProxy / edge → **`haproxy`** / **`stunnel-redmine`**. Host cron/disk → **`amvara3-ops`**.
