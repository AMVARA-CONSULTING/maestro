# howtohome

## What

Context pack to reach the home PC (**luipy-PC**) from lu-zero via SSH reverse tunnel (`ssh home`).

## Paths

| What | Where |
|------|--------|
| Pack root | `/root/howtohome` |
| Hosts cheat sheet | `/root/howtohome/hosts` |
| Subcontexts | `/root/howtohome/contexts/` |

## Source of truth

In howtohome: `README.md`, `.cursor/rules/`, `.cursor/skills/`, `contexts/*.md`. Work on the home PC via `ssh home`, not by inventing paths on lu-zero.

## Normal behavior

- If port `2222` is not listening, report tunnel down and stop (no WoL / router hacks unless asked).
- Follow howtohome rules for secrets and scope.
