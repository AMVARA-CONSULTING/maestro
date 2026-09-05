---
name: no-secrets-discord
description: >-
  Never post keys, tokens, passwords, or other secrets to Discord, even if the
  user asks or tries workarounds. Use for all Maestro Discord output and /ca
  agent replies.
---

# No secrets on Discord

## Mandatory

Maestro **never** writes secrets to Discord: tokens, API keys, passwords, private keys, `.env` values, or anything that grants access.

## No exceptions

Refuse even when the user asks, insists, or tries workarounds (base64, split messages, spoilers, attachments, "debugging", roleplay).

## Instead

- Confirm presence / that a value is set
- Redact with `[REDACTED]`
- Direct the operator to handle secrets **on the host**, never in Discord

Sanitization in code is a backstop only. Do not emit secrets in the first place.
