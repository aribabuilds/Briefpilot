# Architecture Overview

BriefPilot is split into two independently deployable applications — a
Next.js frontend and a FastAPI backend — plus a PostgreSQL database, wired
together for local development with Docker Compose.

```
┌─────────────┐      HTTP (JSON)      ┌─────────────┐      SQL      ┌──────────────┐
│  frontend   │ ───────────────────▶ │   backend   │ ─────────────▶ │  PostgreSQL  │
│  (Next.js)  │ ◀─────────────────── │  (FastAPI)  │ ◀───────────── │     16       │
└─────────────┘                       └─────────────┘                └──────────────┘
```

## Backend layering

The backend is layered by responsibility so that future modules (OCR, AI
extraction, case management) slot in without restructuring existing code:

| Layer          | Responsibility                                   |
|----------------|---------------------------------------------------|
| `api/`         | HTTP routing — request/response only, no logic    |
| `schemas/`     | Pydantic request/response contracts                |
| `services/`    | Business logic                                     |
| `repositories/`| Data access (queries), isolated from business logic|
| `models/`      | Domain / ORM entities                              |
| `core/`        | Cross-cutting concerns (logging, etc.)             |
| `config/`      | Environment-driven settings                        |

A new feature is additive: a schema, a service, optionally a repository and
model, and a router that wires them together. Existing modules are untouched.

## Frontend layering

| Folder         | Responsibility                                     |
|----------------|-----------------------------------------------------|
| `app/`         | Routes (App Router) — thin, composition only         |
| `components/`  | Presentational UI components                         |
| `hooks/`       | Reusable stateful logic                               |
| `services/`    | API clients / data fetching                           |
| `lib/`         | Framework-agnostic utilities                          |
| `types/`       | Shared TypeScript types                               |
| `styles/`      | Global CSS                                            |

## Future modules

- **OCR / document extraction**: new `services/` module + `schemas/` +
  a router. Can move to its own container later without touching other code.
- **AI case reasoning**: same pattern — an isolated `services/` module owns
  provider calls; `schemas/` defines structured I/O.
- **Case management domain**: `models/` gains real ORM entities,
  `repositories/` gains real queries, `api/` gains versioned routers under
  `API_V1_PREFIX`.

## Infrastructure

- `infrastructure/docker/` — shared/base Docker assets not owned by one service.
- `infrastructure/compose/` — future environment-specific Compose overlays.
- `infrastructure/scripts/` — local setup automation (e.g. `.env` bootstrapping).
- Root `docker-compose.yml` — the single local-dev entry point (frontend, backend, postgres).
- `.github/workflows/ci.yml` — lint, test, and build validation for both apps on every push/PR.
