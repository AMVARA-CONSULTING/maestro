# d-writer

## What

**Dyson Project** modular editorial engine on **amvara4**: script/narrative generation loop (pi harness + Python engine). Writer model is served by **Ollama on amvara8** (not on amvara4).

## Paths (on amvara4)

| What | Where |
|------|--------|
| Repo | `/root/Repos/d-writer` |
| Writer system / AGENTS | `writer-system/` |
| Engine / config | `engine/`, `config.yaml`, `OPERACION.md` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara4 'ls /root/Repos/d-writer; head -n 40 /root/Repos/d-writer/README.md'
```

## Source of truth

On the amvara4 tree: `README.md`, `OPERACION.md`, `writer-system/AGENTS.md`, project `.cursor/` if present.

## Normal behavior

- Do not assume Ollama runs on amvara4; model host is **amvara8**.
- Prefer read-only inspection of outputs/config unless asked to run or change the loop.
- Never post secrets or API keys to Discord.
