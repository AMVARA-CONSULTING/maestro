# automail.lu-zero.ldeluipy.es

## What

Automail helper site and small PHP API.

## Paths

| What | Where |
|------|--------|
| Docroot | `/var/www/automail.lu-zero.ldeluipy.es` |

## Source of truth

`api/`, `lib/`, and Apache vhost. Never expose mail credentials or `.env` to Discord.

## Normal behavior

- Inspect before mutate; keep secrets host-side only.
