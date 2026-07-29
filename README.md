# BriefPilot

AI Case Manager for German Bureaucracy.

Upload a photo or PDF of a German official letter and get its text extracted
via a real OCR pipeline (ingestion → preprocessing → Tesseract), with a
quality gate that asks you to retake an unreadable photo instead of showing
garbled output. See [PROGRESS.md](PROGRESS.md) for exactly what's built and
what's still ahead — classification, structured extraction, and the
plain-English explanation land in Sprint 2. There is no authentication (by
design — see [ADR-0001](docs/adr/0001-local-first-zero-cost-demo-strategy.md))
and no hosted deployment.

## Architecture overview

```
┌─────────────┐      HTTP (JSON)      ┌─────────────┐      SQL      ┌──────────────┐
│  frontend   │ ───────────────────▶ │   backend   │ ─────────────▶ │  PostgreSQL  │
│  (Next.js)  │ ◀─────────────────── │  (FastAPI)  │ ◀───────────── │     16       │
└─────────────┘                       └─────────────┘                └──────────────┘
```

- **Frontend**: Next.js (App Router) + TypeScript + React + Tailwind CSS
- **Backend**: Python 3.13 + FastAPI + Pydantic v2 + Uvicorn, layered as
  `api → services → repositories → models`, fully type-hinted and checked
  with `mypy --strict`
- **AI integration**: provider-agnostic `AIService` abstraction
  (`backend/app/services/ai/`) — business logic depends only on the
  interface; OpenAI/Azure OpenAI are swappable adapters (see
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md))
- **Database**: PostgreSQL 16, run via Docker
- **Dev/CI**: Docker Compose for local orchestration, GitHub Actions for
  lint/type-check/test/build validation

Full rationale for the folder structure and how future modules (OCR, AI,
case management) will fit in is documented in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Folder structure

```
briefpilot/
├── frontend/                  Next.js app (TypeScript, Tailwind, ESLint, Prettier)
│   └── src/
│       ├── app/                Routes (App Router)
│       ├── components/         Presentational UI components
│       ├── lib/                Framework-agnostic utilities
│       ├── hooks/               Reusable stateful logic
│       ├── services/            API clients / data fetching
│       ├── types/               Shared TypeScript types
│       └── styles/              Global CSS
├── backend/                   FastAPI app (Pydantic v2, Uvicorn)
│   └── app/
│       ├── api/                 HTTP routers
│       ├── core/                Cross-cutting concerns (logging, ...)
│       ├── config/               Environment-driven settings
│       ├── models/               Domain / ORM entities
│       ├── schemas/              Pydantic request/response contracts
│       ├── services/             Business logic
│       │   └── ai/                AIService abstraction + OpenAI/Azure adapters
│       ├── repositories/         Data access
│       ├── utils/                Shared helpers
│       └── tests/                Pytest test suite
├── infrastructure/
│   ├── docker/                 Shared/base Docker assets
│   ├── compose/                 Future Compose overlays (prod, test, ...)
│   └── scripts/                 Setup automation (e.g. .env bootstrapping)
├── docs/                       Architecture documentation
├── .github/workflows/          CI pipeline
├── docker-compose.yml          Local orchestration: frontend + backend + postgres
└── .env.example                Root-level env vars for Docker Compose
```

## Local development

### Quick start

```bash
make env      # create .env files from the templates
make install  # backend + frontend deps, and register git hooks
make dev      # run the whole stack via Docker Compose
```

Then open `http://localhost:3000` (frontend) and `http://localhost:8000/health` (backend).
`make help` lists every target. On Windows, `make` is not installed by default —
either `choco install make`, or run the underlying commands shown in the
[Makefile](Makefile); every target is a thin wrapper with nothing hidden.

There is intentionally **no hosted deployment** — see
[ADR-0001](docs/adr/0001-local-first-zero-cost-demo-strategy.md).

### Prerequisites

- Node.js 22+
- Python 3.13+
- Docker Desktop (for Postgres and/or full-stack runs)

### 1. Bootstrap environment files

```bash
# macOS/Linux
bash infrastructure/scripts/setup-env.sh

# Windows PowerShell
./infrastructure/scripts/setup-env.ps1
```

This copies `.env.example` → `.env` at the root, and inside `frontend/` and
`backend/`. Adjust values as needed — including `AI_PROVIDER` and the
matching provider credentials (see "AI provider configuration" below).

### 2. Run the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Check `GET /health` and `GET /version`.

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

### 4. Database

Postgres is only provided via Docker (see below) — there is no local install
step. Start just the database with:

```bash
docker compose up postgres
```

## Docker commands

Start the full stack (frontend, backend, Postgres):

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up -d --build
```

Stop and remove containers:

```bash
docker compose down
```

Stop and also remove the Postgres volume (destructive — wipes local DB data):

```bash
docker compose down -v
```

View logs for one service:

```bash
docker compose logs -f backend
```

## Testing on a real phone (LAN)

The frontend bakes `NEXT_PUBLIC_API_URL` in at **build time**. The default,
`http://localhost:8000`, works from a browser on the same machine — but from
a phone, "localhost" means the phone itself, not your computer. To actually
photograph a letter with a phone camera, point both apps at your machine's
LAN IP instead of `localhost`:

1. **Find your LAN IP** (same Wi-Fi as the phone):
   - Windows: `ipconfig` → the `IPv4 Address` under your active adapter
   - macOS/Linux: `ifconfig` or `ip addr` → look for `192.168.x.x` / `10.x.x.x`
2. **Set it in both `.env` files** before starting the stack:
   ```bash
   # frontend/.env
   NEXT_PUBLIC_API_URL=http://<your-lan-ip>:8000

   # backend/.env
   CORS_ORIGINS=http://<your-lan-ip>:3000
   ```
3. `make dev` (or the two dev-server commands above), then on the phone's
   browser (same Wi-Fi) go to `http://<your-lan-ip>:3000`.

Rebuild the frontend after changing `NEXT_PUBLIC_API_URL` — Next.js inlines
`NEXT_PUBLIC_*` variables at build time, so `npm run dev` picks up a changed
`.env` on restart, but a production build (`npm run build`) needs rebuilding.

## AI provider configuration

The backend never calls an AI provider SDK directly outside
`backend/app/services/ai/` — everything else depends on the `AIService`
interface (`app/services/ai/base.py`) and resolves a concrete adapter through
`get_ai_service()`. Switch providers with one env var, no code changes:

| Variable                    | Used when                  |
|------------------------------|-----------------------------|
| `AI_PROVIDER`                 | `openai` (default) or `azure_openai` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | `AI_PROVIDER=openai`     |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` | `AI_PROVIDER=azure_openai` |

Adding a new provider (Anthropic, Gemini, ...) means adding one adapter class
under `app/services/ai/providers/` and a branch in
`app/services/ai/factory.py` — routers, services, and schemas that depend on
`AIService` are untouched. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#ai-provider-abstraction-dependency-inversion)
for the full rationale.

## Coding standards

**Python** (backend): `black` (formatting), `ruff` (linting), `isort` (import
ordering), `mypy --strict` (type checking — all functions, classes, and
schemas are expected to be fully typed). Config lives in `backend/pyproject.toml`.

```bash
cd backend
black app
ruff check app --fix
isort app
mypy app
pytest
```

**TypeScript** (frontend): ESLint (`eslint-config-next` + flat config) and
Prettier (with `prettier-plugin-tailwindcss` for class sorting).

```bash
cd frontend
npm run lint
npm run format
```

**Git hooks.** `make install` registers [pre-commit](.pre-commit-config.yaml), which
runs formatters and linters on staged files. The hooks deliberately cover formatting
and linting only — mypy, eslint and pytest stay in CI and `make ci`, because a commit
hook slow enough to be annoying gets bypassed with `--no-verify`, and a bypassed hook
protects nothing.

Run the entire CI suite locally before pushing:

```bash
make ci
```

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

- **frontend**: `npm ci` → `npm run lint` → `npm run format:check` → `npm run build`
- **backend**: install deps → `ruff check` → `black --check` → `isort --check-only` → `mypy` → `pytest`

Deployment is intentionally not configured — that is a decision, not an omission.
See [ADR-0001](docs/adr/0001-local-first-zero-cost-demo-strategy.md).

## Project documentation

| File | Purpose |
|------|---------|
| [PROGRESS.md](PROGRESS.md) | Milestone tracker (M1–M30) and known deviations |
| [BACKLOG.md](BACKLOG.md) | Scope-freeze register: what's out, and why |
| [LEARNING.md](LEARNING.md) | Decisions log and milestone reviews |
| [docs/adr/](docs/adr/) | Architecture Decision Records |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System structure and layering |
