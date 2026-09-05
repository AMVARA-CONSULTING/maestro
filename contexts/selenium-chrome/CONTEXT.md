# selenium-chrome

## What

**Selenium standalone Chrome** on **amvara6** (Docker). Used as a browser automation lab dependency (often alongside Cognos work, but Cognos itself is **out of this catalog**).

For **Maestro / cursor-agent** page checks, login verify, and interactive browse: prefer catalog **`chrome-mcp`** on **amvara2** (CDP + DevTools MCP). Use this Selenium stack when you need WebDriver, noVNC/VNC live view, or Cognos-lab flows. Skill: `.cursor/skills/browser-tools/SKILL.md`.
## Paths (on amvara6)

| What | Where |
|------|--------|
| Compose dir | `/root/cognos_containerization/cognos-podman-deployment` |
| Compose file | `docker-compose-selenium-chrome.yml` |
| Container (typical) | `selenium-chrome` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara6 'docker ps --filter name=selenium; docker compose -f /root/cognos_containerization/cognos-podman-deployment/docker-compose-selenium-chrome.yml ps'
```

## Source of truth

That compose file and live container status on amvara6.

## Normal behavior

- Prefer status/logs unless asked to recreate/restart the container.
- Do not expand scope into Cognos Podman stacks unless Luipy binds/adds that project.
- **Tab/window hygiene:** max 1 window; keep tabs minimal (prefer ≤2). Rule: `.cursor/rules/maestro-browser-tools.mdc`.
- Never post secrets to Discord.
- Host disk/cron → **`amvara6-ops`**. Agent-preferred browser → **`chrome-mcp`**.
