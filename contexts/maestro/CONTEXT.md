# Maestro (self)

## What

Discord ultra-orchestrator for Luipy on **lu-zero**. Slash commands, NL @mention routing, cursor-agent `/ca`.

## Paths

| What | Where |
|------|--------|
| Repo / runtime | `/root/bots/maestro` |
| Catalog | `catalog/hosts/*.json` |
| Context packs | `contexts/<id>/` |
| Systemd | `maestro.service` |

## Source of truth

Read first in this repo: `README.md`, `.cursor/rules/`, `.cursor/skills/`, `prompts/`.

## Normal behavior

- Luipy only. No secrets on Discord.
- **Discord homes (dual-home):** `config.json` → `discord.homes[]` (`guild_id` + `channel_id`). NL and `/ca_persist` accept any listed channel; slash commands sync to every listed guild. Legacy single `guild_id`/`channel_id` still works. Override: `DISCORD_HOMES=guild:channel,guild:channel`.
- **Never compromise end-user data:** no deletes/wipes of OpenCloud user files, mailboxes, or tenant media unless Luipy gives an explicit scoped confirmation. Rule: `.cursor/rules/maestro-protect-user-data.mdc` · skill: `protect-user-data`.
- Phase 2: resolve projects via multi-host catalog; inject the matching pack; prefer the **project tree on the catalog host** for detailed rules/skills (`AGENTS.md`, `.cursor/`).
- cursor-agent always runs on **lu-zero** (Maestro). Remote hosts (`lu-one`, `lu-oracle`, `amvara2`, `amvara3`, `amvara4`, `amvara6`, `amvara8`, `amvara9`, `amvara10`) are reached with SSH.
- Do not invent catalog entries. Minecraft on **lu-zero** is out of catalog (backup/off); live MC is on **lu-one**. **lu-oracle** is ops-only unless Luipy adds apps. Other Amvara hosts are not catalogued unless asked; fleet SSH practices live under **`amvarabridge`** when that project is bound.
- **Restart:** only Luipy via Discord `/restart_maestro` (host CLI `restart_guard operator` only without `MAESTRO_AGENT=1`). Agents must never restart the service. `contexts/` edits do not need a restart.
- Image attachments on Discord messages are cached under `data/attachments/` for cursor-agent `Read`, purged on `/thread_end`, TTL 72h. Also PDF / logs / text-like files.
- `/stop_ca` (persist threads only): stop the current resume for **this** thread and drop its queue; other threads and root `/ca` are not affected. Busy status keeps a **Stop** button for the whole run.
- **Outbound images:** agent saves PNG/JPEG under `data/outbound/<thread_id>/` (or `_oneshot/…`); Maestro attaches them to the Discord reply after the turn.
- `/thread_end` posts a short session summary to the parent Discord channel before deleting the thread.
- Persist thread title: `{project|slug} · {host} · {cursor-stamp}` (first 8 hex chars of Cursor chat id; not Discord HHMM). Echoes **Original msg:** with the first operator prompt into the thread.
- **Autoagents:** catalog flag `autoagents.{rel_dir,loop}` marks installs. Skill: `.cursor/skills/autoagents/SKILL.md`. Template reference: `/root/Repos/autoagents`. When asked: write tasks, check/start loop, notify (no confirm unless discuss-first).
- **Browser tools:** prefer catalog **`chrome-mcp`** (amvara2); fallback **`selenium-chrome`** (amvara6). Skill: `.cursor/skills/browser-tools/SKILL.md`. Hard limits (1 window, ≤2 tabs): `.cursor/rules/maestro-browser-tools.mdc`. lu-zero MCP: `/root/.cursor/mcp.json` → **`chrome`** via `scripts/chrome-mcp-stdio.sh`.
- **Redmine (MaestroBot):** API user for notes/tickets. Secrets in `.env` (`REDMINE_*`). Catalog field `redmine_doc_issue_id` (this project: **#8066**). Orphan close notes → Lost & Found **#8077**. Skill: `.cursor/skills/redmine-notes/SKILL.md`. Rule: `.cursor/rules/maestro-redmine-notes.mdc`. Notes = ASD-STE100 English inside Textile `{{collapse(Title · Project · cursor-stamp)}}` (first 8 hex chars of Cursor chat id; not issue id / not Discord HHMM). **Textile only — never Markdown in journals.** On `/thread_end`, runtime posts **one** close note: catalog hub → else one primary mentioned work ticket → else `#8077` (no fan-out). App host = amvara3; public URL via stunnel.
- **OpenCloud hangar (Maestro Space):** account `maestro@km0digital.com`; credentials `OPENCLOUD_*` in `.env`. Folders: `human_input/` (humans→Maestro), `maestro_input/` (Maestro→humans), `others/`. Skill: `.cursor/skills/opencloud-space/SKILL.md`. CLI: `scripts/opencloud_space.py`. Never post tokens to Discord.
