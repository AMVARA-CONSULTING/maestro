# amvara3-dbs

## What

**Auxiliary database** containers on **amvara3** used for lab/testing (MySQL, MongoDB, and related compose files). Not the Redmine Postgres (that lives under **`redmine`**).

## Paths (on amvara3)

| What | Where |
|------|--------|
| Compose ymls | `/var/www/cometa/db/` (`mysql.yml`, `mongodb.yml`, `postgres.yml`, `mssql.yml`, …) |
| Typical running | `mysql_db`, `mongo_database` (names may vary) |

Compose project names seen historically: `db`, `database`.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara3 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | head -30; ls /var/www/cometa/db'
```

## Source of truth

Files under `/var/www/cometa/db/` and live `docker ps` / `docker compose ls`.

## Normal behavior

- Prefer read-only status unless asked to change a specific DB compose.
- **Never** paste credentials from compose/env files to Discord (some ymls contain test passwords).
- Cometa application stack is shut down on this host and **out of catalog**; do not treat this pack as “bring Cometa back” unless Luipy asks.
