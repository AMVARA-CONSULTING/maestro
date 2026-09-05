---
name: browser-tools
description: >-
  Fleet browser automation for Maestro: prefer amvara2 chrome-mcp (CDP/MCP);
  fallback amvara6 selenium-chrome. Use when Luipy asks to open a site, verify
  UI/login, scrape, Google Maps, or any real-browser check.
---

# Browser tools (fleet)

## Prefer

| Priority | Catalog id | Host | When |
|----------|------------|------|------|
| **1** | **`chrome-mcp`** | **amvara2** | Agent navigate / DOM / screenshots / login checks / Maps-style flows |
| **2** | **`selenium-chrome`** | **amvara6** | WebDriver scripts, Cognos lab, or live view via noVNC/VNC |

Also on **lu-zero** (not a catalog browser project): `/root/Repos/webs-marketing/agents/chrome-mcp-wrapper.sh` for marketing scrapers (`chrome-devtools-mcp` + CDP `9222`). Prefer fleet **`chrome-mcp`** for general Maestro work.

## Hard limits (always)

- **Max 1 window.** Never spawn a second Chromium / second debug port (e.g. 9223).
- **Max 2 tabs.** Prefer **1**; reuse by navigating the existing tab.
- After a browser session: leave **exactly one** page target (or run cleanup).
- Never dump cookies, passwords, or auth headers to Discord.

## chrome-mcp (amvara2) — how to use

Pack: `contexts/chrome-mcp/CONTEXT.md`. Path: `/home/amvara/projects/chrome-mcp`.

```bash
ssh amvara2 'cd /home/amvara/projects/chrome-mcp && ./scripts/status.sh'
ssh amvara2 'cd /home/amvara/projects/chrome-mcp && ./scripts/start.sh'    # if CDP down
ssh amvara2 'cd /home/amvara/projects/chrome-mcp && ./scripts/close-extra-tabs.sh'
```

- CDP: `http://127.0.0.1:9222` on amvara2 only.
- **From lu-zero / Maestro `/ca`:** MCP server **`chrome`** in `/root/.cursor/mcp.json`, wrapper `/root/bots/maestro/scripts/chrome-mcp-stdio.sh` (SSH stdio → remote `mcp-stdio.sh`). Use MCP tools when available; if the server is down, start CDP on amvara2 then retry.
- On amvara2 Cursor itself: `scripts/mcp-stdio.sh` / `config/cursor-mcp.json`.
- Do not invent a second local Chrome on lu-zero for fleet work.

## selenium-chrome (amvara6) — fallback

Pack: `contexts/selenium-chrome/CONTEXT.md`.

```bash
ssh amvara6 'docker ps --filter name=selenium'
# WebDriver :4444 · VNC :5900 · noVNC :7900 (on amvara6)
```

Prefer status/logs; recreate/restart only when asked or clearly dead and needed.

## Workflow

1. Need a real browser? Read this skill + the matching CONTEXT pack.
2. Prefer **`chrome-mcp`**: ensure CDP up → do work → **close extra tabs**.
3. Use Selenium only if the task needs WebDriver/noVNC or chrome-mcp cannot serve it.
4. Never post secrets. Respect protect-user-data for any account content.
