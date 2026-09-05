---
name: opencloud-space
description: >-
  Use Maestro Space on OpenCloud (cloud.km0digital.com) as a file hangar:
  list, download, and upload via WebDAV. Use when Luipy asks to read/write
  Space files, share artifacts, or park inputs for Maestro.
---

# OpenCloud Maestro Space (hangar)

## When to use

- Luipy asks to **read**, **list**, **upload**, or **fetch** files in OpenCloud / Maestro Space.
- Need a durable place for artifacts (logs, images, exports) beyond Discord attachment TTL.
- Operator says a file is “in the Space”, `human_input`, `maestro_input`, or `others`.

Do **not** use this for random OpenCloud user homes or other spaces unless Luipy scopes that explicitly. Default hangar = **Maestro Space** only.

## Hangar layout

| Folder | Purpose |
|--------|---------|
| `human_input/` | Luipy / humans drop files **for Maestro to read** |
| `maestro_input/` | Maestro writes files **for humans / later use** |
| `others/` | Misc shared files (neither clear channel) |

## Credentials (host only)

In `/root/bots/maestro/.env` (never Discord):

| Key | Role |
|-----|------|
| `OPENCLOUD_URL` | `https://cloud.km0digital.com` |
| `OPENCLOUD_USER` | `maestro@km0digital.com` |
| `OPENCLOUD_APP_TOKEN` | App token (Basic auth; password Basic is disabled) |
| `OPENCLOUD_PASSWORD` | Account password (Dex login; prefer app token for API) |
| `OPENCLOUD_SPACE_ID` | Maestro Space drive id |
| `OPENCLOUD_SPACE_NAME` | `Maestro Space` |

Renew app token on amvara10 when expired:

```bash
ssh amvara10 'docker exec opencloud-opencloud-1 opencloud auth-app create --user-name maestro@km0digital.com --expiration 2160h'
# Parse line " token: …" → update OPENCLOUD_APP_TOKEN (+ EXPIRES_AT) in Maestro .env
```

## CLI (preferred)

```bash
python3 /root/bots/maestro/scripts/opencloud_space.py folders
python3 /root/bots/maestro/scripts/opencloud_space.py ls human_input/
python3 /root/bots/maestro/scripts/opencloud_space.py get human_input/file.png -o /tmp/file.png
python3 /root/bots/maestro/scripts/opencloud_space.py put /tmp/out.txt maestro_input/out.txt
```

Auth is WebDAV Basic (`user` + **app token**) against the public cloud URL from lu-zero. No SSH hop required for normal list/get/put.

## Safety

- **No secrets on Discord** (tokens, passwords, `.env`).
- **Protect user data:** do not delete/wipe Space contents unless Luipy scopes a specific delete.
- Prefer **read** `human_input/`; prefer **write** `maestro_input/`.
- Images for Discord replies: download then copy PNG/JPEG to the session `data/outbound/<thread_id>/` when Luipy should see them.

## Related

- Pack: `contexts/opencloud/` (stack ops on amvara10).
- Rule: `.cursor/rules/maestro-opencloud-space.mdc`.
- Redmine hub for cloud stack: `#7530`.
