---
name: redmine-notes
description: >-
  Post Redmine journal notes and tickets as MaestroBot (API). Use when Luipy asks
  to add a Redmine note, create/update an issue, when a session mentions tickets,
  or on material ops that need a durable trail. Notes must be ASD-STE100 English
  inside a Textile collapse. Catalog field redmine_doc_issue_id is the project hub.
---

# Redmine notes (MaestroBot)

Not an MCP server. It is a **Maestro skill + catalog field + runtime helper**:

| Layer | Role |
|-------|------|
| Catalog `redmine_doc_issue_id` | Per-project documentation / hub ticket |
| Skill + rule | How agents write notes during `/ca` |
| `maestro/redmine_notes.py` | API client + `/thread_end` auto close notes |
| `.env` `REDMINE_*` | Secrets (never Discord) |

## Account

| Field | Value |
|-------|--------|
| Login | `MaestroBot` (user id `86`) |
| Public URL | `https://redmine.amvara.de` |
| Secrets | `/root/bots/maestro/.env` → `REDMINE_URL`, `REDMINE_API_KEY`, `REDMINE_USER_LOGIN`, `REDMINE_DEFAULT_ISSUE_ID` |
| Maestro product hub | `#8066` via catalog id `maestro` |
| Lost & Found (orphan close notes) | `#8077` (`REDMINE_DEFAULT_ISSUE_ID`) |

**Never** print `REDMINE_API_KEY` to Discord.

Ultron reference (behavior only): `amvara4:/root/Repos/ultron-redmine/ultron/redmine.py` (`PUT /issues/{id}.json` with `issue.notes`).

## Lookup (read)

- **Default:** Redmine REST API (`/search.json`, `/issues/{id}.json`).
- **Writes (notes/tickets):** always API as MaestroBot.
- **Hard / exact text search** (journals, precise subject): read-only SQL on amvara3 `redmine_postgres` when API search is weak or slow. **SELECT only.** See `contexts/redmine/CONTEXT.md` → Lookup policy.

## Catalog field

In `catalog/hosts/<host>.json` projects:

```json
"redmine_doc_issue_id": 7530
```

- Shown in `/list_projects` as `RM#7530`.
- Injected into persist session context when the project is bound.

### Close-note target (exactly ONE)

On `/thread_end`, MaestroBot posts **one** close note. Hierarchy:

1. **Catalog hub** (`redmine_doc_issue_id`, or KM0 fallback `#7594`) when the project is bound.
2. Else **one** primary work ticket mentioned by the operator (first non-hub id).
3. Else **Lost & Found `#8077`**.

Never fan-out to every `#issue` that appeared in the chat or in agent tables.

Known hubs:

| Catalog id | Doc ticket |
|------------|------------|
| `maestro` | `8066` |
| `opencloud` | `7530` |
| `km0-web` | `7529` |
| `km0-mail` | `7605` |
| KM0 fallback | `7594` |
| Global orphan / Lost & Found | `8077` |

KM0 family without a specific `redmine_doc_issue_id` (`km0-auth`, `sunday-updates`, …) uses **#7594** for close notes.

If a non-KM0 project has no `redmine_doc_issue_id`, ask Luipy before inventing one (close notes still fall back to one primary mention, else `#8077`).

## When to write (during a session)

1. Luipy asks for a Redmine note / ticket update.
2. Material work happened on **one** clear work ticket → post mid-session note to **that** ticket only.
3. Project-level documentation trail → catalog hub.
4. On `/thread_end`, runtime posts the automatic close note (agents do not duplicate unless Luipy asks).

Do not spam. One clear note beats many fragments. Never post the same close text to many tickets.

### Close-note body style (same as mid-session)

Runtime close notes must match mid-session journals:

* Topic `Session update · <project> · <cursor-stamp>`
* One short lead sentence, then Textile bullets (`* item`)
* No metadata dump (issue id, Discord thread name, stamp repeats)
* No `<pre>` dump of the Discord summary
* No “posted automatically” footer

## Note format (mandatory)

1. **Language:** **English only** for the entire note body (collapse title topic may stay English too).
   - Discord may be Spanish/Catalan; **never** paste operator chat or Discord summaries in another language into a journal.
   - Paraphrase intent in English. Do not mix Spanish and English in one note.
   - `/thread_end` close summaries that feed Redmine must also be English (runtime prompt enforces this).
2. **Style:** ASD-STE100 (short sentences, active voice, one idea per sentence, simple tenses).
3. **Markup:** Redmine **Textile only**. **Never Markdown.**
4. **Wrap** the whole body in a collapse:

```textile
{{collapse(Title · Project · cursor-stamp)

Your ASD-STE100 Textile text here.

}}
```

Title pattern: short topic · catalog project id · **Cursor chat stamp**.

The third field is the **first 8 hex characters** of the Cursor chat UUID
(`cursor_chat_id` / session id), e.g. `9b24dbfe-9335-…` → `9b24dbfe`.

It is **not** the Redmine issue id and **not** the Discord thread `HHMM`.

Example: Cursor chat `9b24dbfe-9335-4a0c-be69-d61cf3c57303` →
`Session update · opencloud · 9b24dbfe` (note still goes to issue `#7530`).

### Textile cheatsheet (use these)

| Need | Textile | Forbidden Markdown |
|------|---------|-------------------|
| Strong | `*bold*` | `**bold**` |
| Emphasis | `_italic_` | `*italic*` as MD |
| Inline code | `@code@` | `` `code` `` |
| Link | `"label":url` | `[label](url)` |
| Issue ref | `#8066` or `"#8066":https://redmine.amvara.de/issues/8066` | `[#8066](https://…)` |
| Heading | `h3. Title` | `# Title` / `## Title` |
| Bullet list | `* item` (start of line) | `- item` as MD list |
| Numbered | `# item` | `1. item` |
| Pre / block | `<pre>…</pre>` | fenced ` ``` ` |
| Line break | blank line between ideas | HTML `<br>` unless needed |

Discord replies may use Markdown. **Journal notes must not.**

## How to post (from lu-zero)

```bash
set -a
# shellcheck disable=SC1091
source /root/bots/maestro/.env
set +a
URL="${REDMINE_URL%/}"
ISSUE=7530
# Build JSON payload in a file; never echo $REDMINE_API_KEY.
curl -sS -X PUT "$URL/issues/${ISSUE}.json" \
  -H "Content-Type: application/json" \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  --data-binary @/tmp/redmine-note-payload.json
```

Payload shape: `{"issue":{"notes":"{{collapse(…)\n\n…\n\n}}"}}`

## Discord replies

- Say which issue(s) you updated (id + collapse title + URL).
- Never paste the API key or `.env` lines.
