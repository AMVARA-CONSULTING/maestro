# sunday-updates

## What

**Sunday-updates** tooling/docs under the Amvara tree on **amvara10**. Not a live customer-facing app; catalogued for maintenance/process work.

## Paths (on amvara10)

| What | Where |
|------|--------|
| Project | `/opt/amvara/sunday-updates` |
| Sibling ops scripts | `/opt/amvara/scripts` (catalog **`amvara10-ops`**) |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara10 'ls -la /opt/amvara/sunday-updates'
```

## Source of truth

Files under `/opt/amvara/sunday-updates` on amvara10 (README / scripts there if present).

## Normal behavior

- Do not confuse with KM0 product trees (`km0-web`, mail, auth, opencloud).
- Prefer inspection unless asked to change update automation.
- Never post secrets to Discord.
