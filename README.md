# Maestro (phase 2)

Discord slash + NL **ultra-orchestrator** on **lu-zero** for **Luipy** only.

## Commands

Discord `/help` is the short Team-facing guide (what / quick start / commands / safety). Source: `_HELP` in `maestro/bot.py`.

| Command | Who | What |
|---------|-----|------|
| `/help` | Luipy | Short guide + command list |
| `/ping` | Luipy | Latency check |
| `/list_projects` `[host]` | Luipy | Catalogued projects (omit = all hosts; host is a Discord choice) |
| `/ca` `text` | Luipy | One-shot cursor-agent |
| `/ca_persist` `text` | Luipy | Thread + Cursor chat (`create-chat` + `--resume`) |
| `/stop_ca` | Luipy | **Inside** persist thread: stop that thread's resume + drop its queue (other threads / root untouched) |
| `/thread_end` | Luipy | **Inside** persist thread: close map + **delete** thread |
| `/restart_maestro` `[force]` | Luipy | Restart bot (deferred; `force` kills busy `/ca`) |
| `@Maestro` / reply | Luipy | NL (includes ca_persist / restart); unclear → **ca_persist** |
| Messages in persist thread | Luipy | Auto-resume (busy + FIFO queue max 5; **Stop** on busy status) |
| Outbound images | Agent | Write PNG/JPEG to `data/outbound/<thread_id>/`; bot attaches after the turn |

## Persist sessions

- Map: `data/sessions.json` (`thread_id` ↔ `cursor_chat_id` ↔ workspace)
- **Homes:** `config.json` → `discord.homes[]` (multi guild/channel). NL + `/ca_persist` on any listed channel; slash sync per guild. Env override: `DISCORD_HOMES=guild:channel,...`
- Thread name: `{project|slug from first text} · {host} · {cursor-stamp}` (first 8 hex chars of Cursor chat id; never Discord HHMM; never the literal `none`)
- On open: posts **Original msg:** with the operator's first prompt into the thread (before the first agent turn)
- Image attachments on messages: downloaded to `data/attachments/<thread_id>/` (or `_oneshot/` for NL `/ca`); paths injected for cursor-agent `Read`. Disk check keeps >=512 MiB free after download. Purged on `/thread_end`; TTL 72 h otherwise. Allowed: images, PDF, logs and common text/config suffixes.
- `/thread_end`: LLM summary (resume Cursor chat) posted to the **parent channel**, then thread deleted. If Redmine is configured, MaestroBot posts **one** close note: project `redmine_doc_issue_id` (or KM0 `#7594`) → else one primary mentioned work ticket → else Lost & Found `#8077`.
- Resume failure: buttons Retry / New Cursor session / End thread
- `/stop_ca` + busy **Stop** button: abort current resume for **that thread only**; queue cleared; session kept. **Stop** stays on the Busy status message for the whole run.
- Require **Message Content Intent** (portal + `DISCORD_MESSAGE_CONTENT_INTENT=1`)

## Restart policy

- **Only Luipy** restarts Maestro: Discord **`/restart_maestro`** (NL only if they explicitly ask to restart this bot now).
- **Agents never restart** `maestro.service` (no `systemctl` / `systemd-run` / `restart_guard operator`). Spawned agents get `MAESTRO_AGENT=1`; CLI `operator` is **denied** in that context.
- `contexts/**`, rules, skills, prompts: edit freely; no restart needed.
- Runtime code (`maestro/*.py`, systemd, `.env`): on disk until you run **`/restart_maestro`**.
- Optional hint file: `data/restart-pending` (shown on `/help` / `/ping`).
- `force:True` **SIGKILL**s in-flight `/ca` and persist resumes — prefer waiting until idle.
- **User data:** never delete/wipe end-user content (OpenCloud files, mailboxes, etc.) without explicit scoped confirmation — `.cursor/rules/maestro-protect-user-data.mdc`

## Catalog & context

- Index: `catalog/hosts/*.json` (`lu-zero`, `lu-one`, `lu-oracle`, `amvara2`–`amvara4`, `amvara6`, `amvara8`–`amvara10`, …)
- Packs: `contexts/<id>/CONTEXT.md`
- cursor-agent always on Maestro host; remote projects via SSH from the agent
- lu-zero: no Minecraft in catalog (backup/off). lu-one: live WN + Jarvys + mc-web + ops. lu-oracle: ops-only. amvara2: amvara.de + econsultants + gitlab + haproxy + sentry + stunnel-redmine + chrome-mcp + ops. amvara3: redmine + haproxy + aux DBs + ops. amvara4: Ultron + bridge + d-writer + su-portfolio + ops. amvara6: selenium-chrome + ops. amvara8: ollama + amvara.ai (inspect-only) + vpn + ops. amvara9: pos + ops. amvara10: KM0 web/mail/auth + opencloud + sunday-updates + ops
- Ops packs: `lu-zero-ops`, `lu-one-ops`, `lu-oracle-ops`, `amvara2-ops`, `amvara3-ops`, `amvara4-ops`, `amvara6-ops`, `amvara8-ops`, `amvara9-ops`, `amvara10-ops`
- **Autoagents:** optional per-project flag `autoagents: { rel_dir, loop }` in `catalog/hosts/*.json`. Listed in `/list_projects`. Skill `.cursor/skills/autoagents/SKILL.md`. Base template `/root/Repos/autoagents`.
- **Browser tools:** catalog **`chrome-mcp`** (amvara2, preferred) and **`selenium-chrome`** (amvara6, fallback). Skill `.cursor/skills/browser-tools/SKILL.md`. Rule `.cursor/rules/maestro-browser-tools.mdc` (max 1 window, ≤2 tabs).
- **Redmine doc tickets:** optional `redmine_doc_issue_id` in catalog (shown as `RM#…`). MaestroBot notes via skill `redmine-notes` (**Textile only**, never Markdown). `/thread_end` posts **one** close note: catalog hub → else one primary mentioned work ticket → else Lost & Found `#8077`. Known: `maestro` → 8066, `opencloud` → 7530, `km0-web` → 7529, `km0-mail` → 7605; KM0 fallback `#7594`; orphan `#8077`. Collapse titles use the first 8 hex chars of the Cursor chat id.

## Ops

```bash
# Prefer Discord: /restart_maestro
# Host shell only (must NOT have MAESTRO_AGENT=1):
cd /root/bots/maestro && .venv/bin/python -m maestro.restart_guard operator
# or with force:
cd /root/bots/maestro && .venv/bin/python -m maestro.restart_guard operator --force
systemctl is-active maestro.service
tail -f /root/bots/maestro/maestro.log
```