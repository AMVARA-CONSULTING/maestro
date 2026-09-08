# archify

## What

**Archify** agent skill + Node CLI: typed JSON IR → validated, interactive architecture / workflow / sequence / data-flow / lifecycle HTML (SVG). Tool for Maestro `/ca` sessions when Luipy wants a system map.

Upstream: https://github.com/tt-a1i/archify

## Paths (lu-zero)

| What | Where |
|------|--------|
| Clone | `/root/outils/archify` |
| Skill / CLI root | `/root/outils/archify/archify` |
| Binary | `node …/archify/bin/archify.mjs` |
| Global skill copy | `~/.agents/skills/archify` |
| Maestro skill wrapper | `/root/bots/maestro/.cursor/skills/archify/SKILL.md` |
| Example Maestro map | `/root/bots/maestro/docs/archify/` |

## Reach

Local on **lu-zero** (no SSH). Needs Node ≥18 (nvm `v22` on this host).

```bash
export PATH="/root/.nvm/versions/node/v22.22.2/bin:$PATH"
node /root/outils/archify/archify/bin/archify.mjs doctor
```

## Notes

- Prefer catalog skill **archify** when generating diagrams.
- For Discord delivery: save PNG / JSON / HTML under Maestro `data/outbound/<thread>/`.
- Never put secrets in diagram JSON or captions.
