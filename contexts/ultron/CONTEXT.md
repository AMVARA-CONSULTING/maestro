# Ultron

## What

Discord bot **Ultron**: Redmine slash commands, optional LLM, scheduled listings, allowlisted @mention routing. Runs as **systemd** on **amvara4** (same idea as Maestro on lu-zero).

## Paths (on amvara4)

| What | Where |
|------|--------|
| Repo / runtime | `/root/Repos/ultron-redmine` |
| Systemd | `ultron.service` |
| Config | `config.yaml` + `.env` (secrets — never Discord) |
| State / logs | `data/`, `ultron.log` |
| **Autoagents** | `/root/Repos/ultron-redmine/autoagents/` · loop `ultron-agent-loop.sh` (separate from `ultron.service`) |

Legacy copies under `/home/luipy/…` are not the live service. Docker container `ultron-redmine-bot` is stopped; prefer systemd.

## How to reach from Maestro (lu-zero)

```bash
ssh amvara4 'systemctl status ultron.service --no-pager; ls /root/Repos/ultron-redmine'
```

## Source of truth

On the amvara4 tree: `README.md`, `config.example.yaml`, project `.cursor/` if present.

## Normal behavior

- Confirm **amvara4** / this path before mutating; do not confuse with Maestro or Tor.
- Prefer `systemctl` for Ultron restarts after code changes (operator ask).
- **Autoagents:** `ultron-agent-loop.sh` is the task loop (not the Discord bot systemd unit). Tasks under `autoagents/tasks/`.
- Never paste `.env`, tokens, or API keys to Discord.
- Fleet notify helpers used by amvarabridge may talk **as** Ultron; that workflow lives in catalog **`amvarabridge`**.
