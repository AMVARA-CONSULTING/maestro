---
name: archify
description: >-
  Generate validated architecture, workflow, sequence, data-flow, and lifecycle
  diagrams as self-contained HTML (Archify). Use when Luipy asks for a system
  map, architecture diagram, sequence, data flow, workflow map, or to visualize
  a catalog project / fleet topology.
---

# Archify (Maestro tool)

## Install (canonical)

| What | Where |
|------|--------|
| Upstream clone | `/root/outils/archify` |
| Skill + CLI | `/root/outils/archify/archify/` |
| Global agent skill | `~/.agents/skills/archify` (Cursor skills.sh install) |
| Catalog id | `archify` on **lu-zero** |
| Context pack | `contexts/archify/CONTEXT.md` |

CLI (always use the outils tree):

```bash
export PATH="/root/.nvm/versions/node/v22.22.2/bin:$PATH"
node /root/outils/archify/archify/bin/archify.mjs doctor
node /root/outils/archify/archify/bin/archify.mjs validate <type> <candidate.json> --quality showcase --json
node /root/outils/archify/archify/bin/archify.mjs deliver <type> <candidate.json> <output.html> --quality showcase --json
```

Optional update check (non-blocking): `node /root/outils/archify/archify/scripts/check-update.mjs`. Set `ARCHIFY_UPDATE_CHECK_DISABLED=1` to skip networking.

## When to use

1. Operator asks for a **mapa / diagrama / architecture / sequence / workflow / data flow**.
2. Bound project (or Maestro itself) needs a durable visual map for Discord or docs.
3. Prefer **8–12** core nodes, one primary path, cards for detail.

## Workflow (agent)

1. Read this skill + full contract: `/root/outils/archify/archify/SKILL.md`.
2. Read matching `schemas/` + one `examples/*.json` under `/root/outils/archify/archify/` (shape only).
3. Write candidate JSON under the project (e.g. `docs/archify/` or `/tmp/archify-work/`).
4. `validate … --quality showcase --json` until all showcase checks pass (0 errors / 0 warnings).
5. `deliver … --quality showcase --json` once.
6. For Discord: save artifacts under `data/outbound/<thread_id>/` (PNG from `visual-check` or chrome-mcp; also JSON/HTML). Maestro attaches allowed outbound files after the turn.
7. Do **not** post secrets; diagrams must not embed tokens or `.env` values.

## Authoring notes (Maestro)

- Reply language follows the operator; Archify Viewer UI may fall back to English (`meta.locale` only `en` | `zh-CN`).
- Keep hostnames, paths, ticket ids, and product names exact.
- Fleet tools (chrome-mcp, OpenCloud, Redmine) are peers of projects, not invented topology.
- Default `meta.quality_profile`: `"showcase"`. Omit `meta.visual_preset` unless asked.
- Artifacts for Maestro live under `/root/bots/maestro/docs/archify/` when mapping this bot.

## Do not

- Invent catalog hosts or projects that are not in `catalog/hosts/`.
- Fan-out Redmine notes for every diagram generation mid-session unless Luipy asked for a durable trail.
