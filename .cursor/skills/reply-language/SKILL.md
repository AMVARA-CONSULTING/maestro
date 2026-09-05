---
name: reply-language
description: >-
  Reply exclusively in the language the user writes in or explicitly requests,
  with Catalan as fallback. Use for all Maestro Discord /ca agent output and
  any Maestro-facing chat replies.
---

# Reply language

## Rule (mandatory)

- Answer **exclusively** in the language the user writes in, or the language they ask for.
- If unclear, answer in **Catalan**.
- Almost always the user will write Castilian Spanish or English; still follow the rule above.

## Keep unchanged

- Code, shell commands, paths, env vars, hostnames, URLs, product names.

## Examples

- User writes in Spanish → reply in Spanish.
- User writes in English → reply in English.
- User writes in Catalan → reply in Catalan.
- User writes Spanish but says "answer in English" → English.
- Language ambiguous → Catalan.
