# Jarvys family (lu-one) — shared pack

## What

Two related bots for Withered Nexus on **lu-one**:

| Catalog id | Role | Path on lu-one |
|------------|------|----------------|
| `jarvys` | Discord admin bot (`jarvys.service`) | `/root/bots/minecraft-admin-bot` |
| `jarvys-ingame` | In-game RCON/chat presence (Docker) | `/root/servers/minecraft/withered-nexus/jarvys-ingame-instance` |

## How to reach from Maestro (lu-zero)

```bash
ssh lu-one 'systemctl status jarvys --no-pager'
ssh lu-one 'docker ps --filter name=jarvys-ingame'
```

cursor-agent stays on lu-zero; all inspection/edits on these paths go through **`ssh lu-one`**.

## Source of truth

- Discord bot: README / code under `/root/bots/minecraft-admin-bot` on lu-one.
- In-game instance: compose/config next to withered-nexus on lu-one.

## Normal behavior

- Distinguish Discord bot vs in-game container when restarting or debugging.
- Do not confuse with stopped Minecraft stacks on lu-zero.
