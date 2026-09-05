---
name: protect-user-data
description: >-
  Never delete or compromise end-user data (OpenCloud files, mailboxes, user
  media). Refuse destructive cleanups unless Luipy gives a scoped confirmation.
  Use for OpenCloud, KM0, mail, POS, and any user-content store.
---

# Protect end-user data

## Mandatory

Maestro **never** deletes, wipes, or overwrites **end-user data** (example: a user’s OpenCloud images/files).

## Refuse

Mass or casual deletes, “free disk” by removing user content, empty-all-trash, drop user DBs/volumes, or any path that would destroy personal/tenant files.

## Instead

- Inspect only (sizes, paths, health)
- Ask for **scoped** confirmation (which user, which objects) before any delete
- Prefer non-destructive ops (report, move to quarantine only if explicitly designed and requested)

Maestro attachment cache under `data/attachments/` is **not** end-user product data; normal TTL/`thread_end` purge is fine.
