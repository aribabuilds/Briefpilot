# BriefPilot

AI Case Manager for German Bureaucracy.

This repository currently contains the **project foundation only**: a clean,
scalable skeleton for the frontend, backend, database, and CI/CD. No business
logic, authentication, OCR, or AI features are implemented yet — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how those will be added later.

## Architecture overview

```
┌─────────────┐      HTTP (JSON)      ┌─────────────┐      SQL      ┌──────────────┐
│  frontend   │ ───────────────────▶ │   backend   │ ─────────────▶ │  PostgreSQL  │
│  (Next.js)  │ ◀─────────────────── │  (FastAPI)  │ ◀───────────── │     16       │
└─────────────┘                       └─────────────┘                └──────────────┘
```

- **Frontend**: Next.js (App Router) + TypeScript + React + Tailwind CSS
- **Backend**: Python 3.13 + FastAPI + Pydantic v2 + Uvicorn, layered as
  `api → services → repositories → models`
- **Database**: PostgreSQL 16, run via Docker
- **Dev/CI**: Docker Compose for local orchestration, GitHub Actions for
  lint/test/build validation

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
`backend/`. Adjust values as needed.

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

## Coding standards

**Python** (backend): `black` (formatting), `ruff` (linting), `isort` (import
ordering). Config lives in `backend/pyproject.toml`.

```bash
cd backend
black app
ruff check app --fix
isort app
pytest
```

**TypeScript** (frontend): ESLint (`eslint-config-next` + flat config) and
Prettier (with `prettier-plugin-tailwindcss` for class sorting).

```bash
cd frontend
npm run lint
npm run format
```

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

- **frontend**: `npm ci` → `npm run lint` → `npm run build`
- **backend**: install deps → `ruff check` → `black --check` → `isort --check-only` → `pytest`

Deployment is intentionally not configured yet.
