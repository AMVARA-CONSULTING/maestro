# LLJA (LaLiga Julio Anguita)

## What

Official competition site: FastAPI API, public frontend, vanilla admin, nginx. Dockerized.

## Paths

| What | Where |
|------|--------|
| Project root | `/srv/llja` |
| Compose | `/srv/llja/docker-compose.yml` |

## Source of truth

In `/srv/llja`: `README.md`, then any `.cursor/` / `AGENTS.md` if present. App code under `backend/`, `frontend/`, `nginx/`.

## Normal behavior

- Use Docker Compose from `/srv/llja`. Prefer inspect before mutate.
- Seed/migrate only when explicitly asked.
