# km0-web

## What

Public marketing site for **KM0 Digital** (Astro) on **amvara10**. Production: km0digital.com (multi-locale).

Also hosts the **ideas webhook receiver** as systemd (not a separate catalog entry).

## Paths (on amvara10)

| What | Where |
|------|--------|
| Repo / deploy | `/opt/km0-web` |
| Compose | `docker-compose.yml` (project `km0`) |
| Nginx (host) | under `nginx/` + system nginx |
| Ideas receiver | `km0-ideas-receiver.service` → webhook on hooks under this tree |
| Env | `.env` (secrets — never Discord) |
| **Autoagents** | `/opt/km0-web/autoagents/` · loop `autoagents-loop.sh` |

## Related (siblings on same host)

| Catalog id | Role |
|------------|------|
| `km0-mail` | Mail stack |
| `km0-auth` | Auth hub |
| `opencloud` | Cloud / Dex / Collabora |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara10 'docker compose -f /opt/km0-web/docker-compose.yml ps; systemctl status km0-ideas-receiver.service --no-pager'
```

## Source of truth

On amvara10: `README.md`, `docs/`, `CONTRIBUTING.md`, project `.cursor/` / agent docs if present.

## Redmine doc ticket

| Field | Value |
|-------|--------|
| Catalog | `redmine_doc_issue_id`: **7529** |
| URL | https://redmine.amvara.de/issues/7529 |
| Subject | [KM0] Web |
| KM0 fallback | **#7594** (use when unsure / no more specific ticket) |
| Notes | MaestroBot · skill `redmine-notes` (ASD-STE100 + collapse; title stamp = first 8 hex chars of Cursor chat id) |

## Normal behavior

- Prefer smallest change; confirm compose/service before restart.
- Ideas-receiver changes stay in this project scope (systemd + hooks under `/opt/km0-web`).
- **Autoagents:** when asked for a task, write under `autoagents/tasks/` per `TASKS-README.md`, verify/start the loop, notify. No confirmation wait unless Luipy asked to discuss first.
- Never post secrets to Discord.
