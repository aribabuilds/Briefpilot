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

## AI provider abstraction (dependency inversion)

External AI providers are treated as interchangeable infrastructure, never as
a dependency the rest of the app codes against directly:

```
app/services/ai/
├── base.py                      AIService — the abstract contract (extract_document, summarize)
├── factory.py                   build_ai_service(settings) / get_ai_service() — selects an adapter
└── providers/
    ├── openai_service.py         OpenAIService(AIService)
    └── azure_openai_service.py   AzureOpenAIService(AIService)
```

- **`AIService`** (`app/services/ai/base.py`) is an `ABC` defining the operations
  the application needs — currently `extract_document` and `summarize` — in
  terms of typed Pydantic DTOs from `app/schemas/ai.py`. Nothing outside
  `services/ai/` may import a provider SDK directly.
- **Adapters** (`OpenAIService`, `AzureOpenAIService`) implement `AIService`
  against a specific provider SDK. Adding a new provider (Anthropic, Gemini,
  ...) means adding one more adapter class here — nothing else changes.
- **`factory.get_ai_service`** reads `Settings.ai_provider` and constructs the
  matching adapter, cached as a singleton (mirrors `get_settings`). It is
  designed to be used as a FastAPI dependency — `Depends(get_ai_service)` —
  so routers and services receive an `AIService`, never a concrete class.

This is the Dependency Inversion Principle applied directly: business logic
and API routes depend on the `AIService` abstraction; concrete providers are
swappable infrastructure wired in at the edge (the factory), selected purely
by the `AI_PROVIDER` environment variable. Switching from OpenAI to Azure
OpenAI (or a future provider) never touches a router, service, or schema that
consumes `AIService`.

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
- **AI case reasoning**: consumes the existing `AIService` abstraction —
  new operations become new abstract methods on `AIService` (implemented by
  every adapter), or a new adapter if a new provider is needed.
- **Case management domain**: `models/` gains real ORM entities,
  `repositories/` gains real queries, `api/` gains versioned routers under
  `API_V1_PREFIX`.

## Infrastructure

- `infrastructure/docker/` — shared/base Docker assets not owned by one service.
- `infrastructure/compose/` — future environment-specific Compose overlays.
- `infrastructure/scripts/` — local setup automation (e.g. `.env` bootstrapping).
- Root `docker-compose.yml` — the single local-dev entry point (frontend, backend, postgres).
- `.github/workflows/ci.yml` — lint, test, and build validation for both apps on every push/PR.
