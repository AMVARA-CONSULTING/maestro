# Tor (audiTor)

## What

Discord bot for Luipy: fleet `/audit` (read-only unless asked to change) and `/ca` via cursor-agent on lu-zero / lu-one / lu-oracle. NL `@Tor` / reply uses the same cursor-agent router pattern as Maestro.

## Paths

| What | Where |
|------|--------|
| Repo | `/root/bots/tor` |
| Systemd | `tor.service` |
| Prompts | `/root/bots/tor/prompts/` |

## Source of truth

In the Tor tree: `README.md`, `.cursor/rules/`, `config.json`, `tor/`.

## Normal behavior

- Do not confuse Tor with Maestro. Tor owns fleet audit/ca; Maestro orchestrates across projects.
- Never Amvara hosts from Tor's policy. Prefer `systemctl` for Tor restarts after code changes.
- NL: Luipy + Tor channel only; fallback unclear → `/ca` on `lu-zero`.
