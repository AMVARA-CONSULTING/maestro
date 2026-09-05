# Withered Nexus (lu-one)

## What

Live **Paper** Minecraft server for Withered Nexus. Runs in Docker on **lu-one** (not the lu-zero backup tree).

## Paths (on lu-one)

| What | Where |
|------|--------|
| Server / compose | `/root/servers/minecraft/withered-nexus` |
| Backups dir | `/root/servers/minecraft/backups` |
| Backup script | `/root/scripts/backup-withered-nexus.sh` |

## How to reach from Maestro (lu-zero)

cursor-agent runs on **lu-zero**. Use SSH:

```bash
ssh lu-one 'cd /root/servers/minecraft/withered-nexus && docker compose ps'
```

Do **not** treat `/root/servers/minecraft/withered-nexus` on lu-zero as live.

## Source of truth

On lu-one under the server tree: compose files, `plugins/`, world data, any `AGENTS.md` / `.cursor/` if present. Prefer inspect via SSH before mutate.

## Normal behavior

- Confirm live vs backup host before changing files or restarting Docker.
- Prefer smallest change; warn before stop/restart of the live container.
