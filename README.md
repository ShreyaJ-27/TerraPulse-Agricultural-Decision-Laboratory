# Vasundara-Agricultural-Decision-Laboratory
# TerraPulse 2.0

Foundation for the TerraPulse agricultural decision laboratory. This repository currently implements Issues 1–3 only: local tooling, shared C1–C8 contracts, and database persistence.

## Setup

Requirements: Node.js 20.11.1, Python 3.14.3, and Docker Desktop for local PostgreSQL/PostGIS. The versions are recorded in `.nvmrc` and `.python-version`.

```powershell
copy .env.example .env
npm install
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
docker compose up -d postgres
alembic upgrade head
```

Run the API with `uvicorn app.main:app --app-dir apps/api --reload` and the frontend with `npm run dev:web`. The API health check is `http://localhost:8000/api/v1/health`.

## Checks

```powershell
npm run typecheck:web
npm run lint:web
npm run build:web
pytest
```

See [docs/contracts.md](docs/contracts.md) and [docs/database.md](docs/database.md) for contract and schema conventions. The migration command requires the local PostGIS container to be running.