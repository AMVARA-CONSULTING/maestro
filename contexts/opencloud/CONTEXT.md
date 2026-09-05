# opencloud

## What

**OpenCloud** stack on **amvara10**: core + Collabora Online, plus **Dex** and **register-api** under the same `/opt/opencloud` tree.

Public cloud: `https://cloud.km0digital.com` (see project README / runbook for full map).

## Sibling: KM0 Auth Hub

Login/register UX is catalog **`km0-auth`** (`/opt/km0-auth`, `auth.km0digital.com`). Dex issuer lives **here**. Treat them as siblings: hub for UX/deploy of the auth pages; this pack for OpenCloud, Collabora, Dex compose, register-api, and IDM-related ops.

## Paths (on amvara10)

| What | Where |
|------|--------|
| Tree root | `/opt/opencloud` |
| OpenCloud compose | `opencloud-compose/` |
| Dex | `dex/` |
| Register API | `register-api/` |
| Nginx / host-www | `nginx/`, `host-www/` |
| Docs | `docs/` (e.g. runbook) |
| **Autoagents** | `/opt/opencloud/autoagents/` · loop `autoagents-loop.sh` (often `var/loop/`) |

## Compose projects (typical)

`opencloud`, `dex`, `register-api` (plus Collabora via compose includes).

## How to reach from Maestro (lu-zero)

```bash
ssh amvara10 'docker compose ls; ls /opt/opencloud'
```

## Source of truth

On amvara10: `README.md`, `docs/runbook.md`, compose trees, project agent docs if present.

## Redmine doc ticket

| Field | Value |
|-------|--------|
| Catalog | `redmine_doc_issue_id`: **7530** |
| URL | https://redmine.amvara.de/issues/7530 |
| Subject | [KM0] OpenCloud |
| KM0 fallback | **#7594** (use when unsure / no more specific ticket) |
| Notes | MaestroBot · skill `redmine-notes` (ASD-STE100 + collapse; title stamp = first 8 hex chars of Cursor chat id) |

## Normal behavior

- Prefer read-only status checks before compose restarts; confirm which sub-stack (core / dex / register-api).
- **User data (absolute):** never delete/wipe OpenCloud user files, shares, or trash contents. Disk cleanup must not target user storage. Inspect quotas/sizes only unless Luipy scopes a specific delete.
- **Autoagents:** write tasks under `autoagents/tasks/`; verify loop process / `var/loop/` when asked for agent work.
- Auth hub pages → **`km0-auth`**. Mail provisioning backend details may touch **`km0-mail`**.
- Never post secrets, tokens, or `.env` to Discord.

## Maestro hangar (ops bridge)

Maestro bot account **`maestro@km0digital.com`** uses project space **Maestro Space** as a file hangar (not a substitute for stack ops).

| Folder | Purpose |
|--------|---------|
| `human_input/` | Operator drops files for Maestro |
| `maestro_input/` | Maestro uploads for the operator |
| `others/` | Misc |

Tooling lives in the **maestro** repo: skill `opencloud-space`, CLI `scripts/opencloud_space.py`, `.env` keys `OPENCLOUD_*`.
