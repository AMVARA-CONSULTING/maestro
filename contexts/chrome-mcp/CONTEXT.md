# chrome-mcp

## What

Persistent **headless Chrome + DevTools MCP** on **amvara2**. Preferred browser tool for Maestro / cursor-agent (navigate, DOM, screenshots, login checks). Distinct from **`selenium-chrome`** on amvara6 (WebDriver / noVNC lab).

## Paths (on amvara2)

| What | Where |
|------|--------|
| Project | `/home/amvara/projects/chrome-mcp` |
| Compose | `docker-compose.yml` (container `chrome-mcp`) |
| Browser image | `selenium/standalone-chrome:152.0.7977.82-20260909` (Chrome CDP only; pinned for CVE-2026-85046). Not Zenika alpine-chrome. |
| CDP | `http://127.0.0.1:9222` (localhost only) |
| MCP stdio | `scripts/mcp-stdio.sh` |
| Cursor snippet | `config/cursor-mcp.json` (`mcpServers.chrome`) |
| Tab cleanup | `scripts/close-extra-tabs.sh` |

## Scripts

| Script | Role |
|--------|------|
| `preflight.sh` | Disk/RAM checks before start |
| `pull-mcp.sh` | Once: pull MCP client image |
| `start.sh` | Bring up Chrome CDP |
| `status.sh` | Compose + CDP health |
| `stop.sh` | Stop stack |
| `smoke-test.sh` | Optional URL smoke |
| `mcp-stdio.sh` | MCP server for Cursor (needs CDP up) |
| `close-extra-tabs.sh` | Keep N page targets (default 1) |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara2 'cd /home/amvara/projects/chrome-mcp && ./scripts/status.sh'
ssh amvara2 'cd /home/amvara/projects/chrome-mcp && ./scripts/start.sh'   # when down; operator OK for start
ssh amvara2 'cd /home/amvara/projects/chrome-mcp && ./scripts/close-extra-tabs.sh'
```

### MCP from lu-zero cursor-agent / Maestro `/ca`

Wired globally on the Maestro host:

| What | Where |
|------|--------|
| MCP config | `/root/.cursor/mcp.json` → server id **`chrome`** |
| Stdio wrapper | `/root/bots/maestro/scripts/chrome-mcp-stdio.sh` (`ssh -T amvara2` → `mcp-stdio.sh`) |
| Approve | `cursor-agent mcp enable chrome` (already done on lu-zero) |

Tools (via MCP `chrome`): `navigate`, `click`, `type`, `screenshot`, `scroll`, `wait_for_selector`, `get_console_logs`, `get_network_errors`, `get_computed_styles`, `mobile_mode`.

CDP stays on amvara2 localhost only; lu-zero never exposes 9222 publicly. If MCP fails, check CDP with `status.sh` / `start.sh` on amvara2.

## Source of truth

On amvara2: `/home/amvara/projects/chrome-mcp/README.md`, compose, `scripts/`. Maestro skill: `.cursor/skills/browser-tools/SKILL.md`. Hard limits: `.cursor/rules/maestro-browser-tools.mdc`.

## Normal behavior

- **Prefer this tool** over Selenium for agent browser work (page checks, login verify, Maps/search flows).
- Prefer status/logs; start only when needed and CDP is down. Do not start a second Chromium on another port.
- **Tab / window hygiene (mandatory):** max **1** browser window; max **2** tabs; reuse tabs (navigate existing); after a session leave **1** page target (or run `close-extra-tabs.sh`). Never leave dozens of tabs (RAM).
- Never post secrets / cookies / CDP dumps with credentials to Discord.
- Host ops → **`amvara2-ops`**. App sites (e.g. econsultants) stay their own catalog packs; this pack is the shared browser.
- Selenium / noVNC → **`selenium-chrome`** on amvara6 (fallback when WebDriver or live VNC view is required).
