# km0-mail

## What

Self-hosted mail stack for **KM0 Digital** on **amvara10**: Postfix, Dovecot, Rspamd, Roundcube, PostgreSQL.

**Service host:** `mail.km0digital.com` · addresses `@km0digital.com`.

## Paths (on amvara10)

| What | Where |
|------|--------|
| Repo / stack | `/opt/km0-mail` |
| Compose | `docker-compose.yml` (project `km0-mail`) |
| Docs / ops | `docs/` |
| Nginx | `nginx/`, host nginx |
| **Autoagents** | `/opt/km0-mail/autoagents/` · loop `autoagents-loop.sh` |

## Related (siblings)

| Catalog id | Role |
|------------|------|
| `km0-web` | Public site |
| `km0-auth` | Auth hub (register may provision mailbox) |
| `opencloud` | Cloud IDM / Dex |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara10 'docker compose -f /opt/km0-mail/docker-compose.yml ps'
```

## Source of truth

On amvara10: `README.md`, `docs/` (runbooks / agent-loop), compose and `config/`.

## Redmine doc ticket

| Field | Value |
|-------|--------|
| Catalog | `redmine_doc_issue_id`: **7605** |
| URL | https://redmine.amvara.de/issues/7605 |
| Subject | [KM0] Email |
| KM0 fallback | **#7594** (use when unsure / no more specific ticket) |
| Notes | MaestroBot · skill `redmine-notes` (ASD-STE100 + collapse; title stamp = first 8 hex chars of Cursor chat id) |

## Normal behavior

- Mail stacks are sensitive: prefer read-only inspection unless asked to change.
- **User data (absolute):** never delete mailbox contents or user mail stores casually; no mass wipe to “free disk”.
- **Autoagents:** task files under `autoagents/tasks/`; check/start `autoagents-loop.sh` when creating work.
- Never post credentials, `.env`, or mailbox secrets to Discord.
- Do not confuse with OpenCloud or auth-hub trees.
