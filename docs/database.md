# Database and persistence

Local development uses PostgreSQL 16 with PostGIS 3.4 through Docker Compose:

```powershell
docker compose up -d postgres
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
alembic upgrade head
```

Set `DATABASE_URL` in `.env` when using a non-default database. The initial migration enables PostGIS and creates the C1–C8 persistence tables, including spatial farm and plot columns in `EPSG:4326`. JSONB is used for scientific payloads and provenance that are intentionally schema-flexible.

Database access is kept behind `apps/api/app/repositories.py`; domain logic does not belong in SQLAlchemy models. Seed/demo records, if added later, must be labelled as development fixtures.
