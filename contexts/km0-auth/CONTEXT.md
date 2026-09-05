# km0-auth

## What

**KM0 Auth Hub** on **amvara10**: central login/registration UI at **https://auth.km0digital.com**.

## Sibling: OpenCloud Dex

Dex issuer stays under catalog **`opencloud`** (`https://cloud.km0digital.com/dex`). This pack is the **hub** (login/register UX + deploy scripts). Cloud/Mail legacy `/login.html` and `/register` redirect here. Register provisions OpenCloud IDM + KM0 Mail mailbox — those backends live in **`opencloud`** and **`km0-mail`**.

When touching SSO/OIDC issuer config → prefer **`opencloud`**. When touching auth hub pages/deploy → this pack.

## Paths (on amvara10)

| What | Where |
|------|--------|
| Project | `/opt/km0-auth` |
| Host www / nginx | `host-www/`, `nginx/` |
| Deploy | `scripts/deploy-auth-hub.sh` |

## How to reach from Maestro (lu-zero)

```bash
ssh amvara10 'ls /opt/km0-auth; head -n 40 /opt/km0-auth/README.md'
```

## Source of truth

On amvara10: `README.md`, `scripts/`, nginx/host-www trees.

## Redmine doc ticket

| Field | Value |
|-------|--------|
| Catalog | no per-project id; **KM0 fallback #7594** |
| URL | https://redmine.amvara.de/issues/7594 |
| Notes | MaestroBot · skill `redmine-notes` (ASD-STE100 + collapse; Cursor chat stamp) |

## Normal behavior

- Cross-check **`opencloud`** (Dex) before changing issuer URLs or client redirects.
- Never post client secrets or `.env` to Discord.
