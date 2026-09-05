# webs-misc (/var/www leftovers)

## What

Small or stub vhosts on lu-zero not given their own catalog entry.

## Typical paths

| Site | Path |
|------|------|
| ping | `/var/www/ping.lu-zero.ldeluipy.es` |
| stats | `/var/www/stats.lu-zero.ldeluipy.es` |
| catchall | `/var/www/catchall.lu-zero.ldeluipy.es` |
| default html | `/var/www/html` |
| lu-zero landing | `/var/www/lu-zero.ldeluipy.es` |
| test | `/var/www/test.ldeluipy.es` |
| susanasubirana | `/var/www/susanasubirana.com` (often empty) |

## Out of this bucket

Larger/important sites have **own catalog ids**: helio03, vault, ldeluipy-es, mcd, automail.  
**mc.ldeluipy.es** lives on **lu-one** (catalog id `mc-web`), not in this lu-zero bucket. Minecraft trees under `/root/servers` on lu-zero are backup/off and **out of catalog**.

## Source of truth

Each docroot + matching Apache site under `/etc/apache2/sites-enabled/`.

## Normal behavior

- Identify the exact vhost before editing. Prefer tiny, explicit changes.
