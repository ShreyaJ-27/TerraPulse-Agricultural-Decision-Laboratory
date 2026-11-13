# TerraPulse — Deployment & Operations Guide

**Team:** Kalakand  
**Date:** November 14, 2026  
**Target Branch:** `feature/terrapulse-complete-platform`

---

## 1. System Requirements & Architecture Overview

TerraPulse is an integrated full-stack agricultural decision laboratory consisting of:
- **Database**: PostgreSQL 16 with PostGIS 3.4 extensions.
- **Backend**: FastAPI 0.115+ (Python 3.11/3.12/3.13) with SQLAlchemy 2.0 and Psycopg 3.
- **Science Engine**: AquaCrop-OSPy 3.1.0 + FAO-56 dual crop coefficient modules.
- **Frontend**: React 18, TypeScript, Three.js, React Three Fiber (R3F), and Vite 5.

```
+---------------------------------------------------------------------------------+
|                                 BROWSER CLIENT                                  |
|   Landing Page (3D R3F)   |   Agricultural Dashboard (8 Tabs)   |   WebGL2 3D   |
|                               http://127.0.0.1:5173/                            |
+---------------------------------------------------------------------------------+
                                       │
                                       │ HTTP / JSON REST
                                       ▼
+---------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                  |
|  /api/v1/farms, /api/v1/crops, /api/v1/agri-calendar, /api/v1/notifications      |
|                               http://127.0.0.1:8000/                            |
|                                                                                 |
|  [ AquaCrop-OSPy Engine ]  [ FAO-56 Engine ]  [ Open-Meteo ]  [ SoilGrids WCS ] |
+---------------------------------------------------------------------------------+
                                       │
                                       │ Async Connection Pool (psycopg)
                                       ▼
+---------------------------------------------------------------------------------+
|                         POSTGRESQL 16 + POSTGIS 3.4                             |
|                           localhost:5433 / terrapulse                           |
+---------------------------------------------------------------------------------+
```

---

## 2. Environment Variables Configuration

Copy `.env.example` or create a `.env` file at the repository root:

```ini
# Database Connection (Host 5433 avoids collisions with native Windows Postgres 5432)
DATABASE_URL=postgresql+psycopg://terrapulse:terrapulse@localhost:5433/terrapulse
TEST_DATABASE_URL=postgresql+psycopg://terrapulse:terrapulse@localhost:5433/terrapulse_test

# Server Configuration
API_V1_STR=/api/v1
PROJECT_NAME="TerraPulse Agricultural Decision Laboratory"
DEBUG=True
HOST=127.0.0.1
PORT=8000

# External APIs
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1
SOILGRIDS_WCS_URL=https://maps.isric.org/mapserv

# Notification & Telegram Integration
TELEGRAM_BOT_TOKEN=demo_token_terrapulse_bot
TELEGRAM_ENABLED=True
QUIET_HOURS_START=22
QUIET_HOURS_END=7
```

---

## 3. Local Deployment Step-by-Step

### Step 1: Start PostgreSQL + PostGIS via Docker

The repository includes a configured `docker-compose.yml` mapped to port `5433`:

```bash
# Start PostGIS container in detached mode
docker compose up -d

# Verify container health
docker compose ps
```

Container details:
- **Image**: `postgis/postgis:16-3.4`
- **Host Port**: `5433` (Container Port: `5432`)
- **User**: `terrapulse`
- **Password**: `terrapulse`
- **Database**: `terrapulse`

### Step 2: Set Up Python Backend & Virtual Environment

```bash
# Activate existing virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install required dependencies
pip install -e .
```

### Step 3: Run Database Migrations

Apply Alembic migrations to create all 26 relational & geospatial tables:

```bash
alembic upgrade head
```

Verify that all tables (`farms`, `plots`, `crop_identities`, `decision_branches`, `farmer_alerts`, `telegram_subscriptions`, etc.) are created.

### Step 4: Seed Interactive Demo Data

Seed the PAU-UAS Joint Agro-Research Station, 3 plots (Maize, Turmeric, Wheat), 10 crops, 750,000L reservoir, decision branches, and 22 daily simulation states:

```bash
python scripts/seed_demo_data.py
```

Expected output:
```
================================================================================
🌱 Seeding TerraPulse Demo Data...
================================================================================
✅ Created Demo Farm: PAU-UAS Joint Agro-Research Station, Ludhiana
✅ Created 3 Plots (Maize, Turmeric, Wheat)
✅ Seeded 10 authoritative crop identities
✅ Initialized Shared Farm Reservoir (750,000 Litres)
✅ Created baseline and counterfactual branches
✅ Seeded 22 daily scientific states
✅ Seeded initial alerts and Telegram subscription
================================================================================
🎉 Seed complete! Demo farm ready at UUID: 00000000-0000-0000-0000-000000000001
================================================================================
```

### Step 5: Start the FastAPI Backend Server

> **Windows Tip**: Python on Windows defaults to `ProactorEventLoop`, which is incompatible with `psycopg` async mode. Always use `run_api.py`, which configures `SelectorEventLoop`:

```bash
python run_api.py
```

The API is now live at:
- **Endpoint**: `http://127.0.0.1:8000`
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **Health Check**: `http://127.0.0.1:8000/health`

### Step 6: Start the Frontend Vite Dev Server

In a separate terminal:

```bash
# Install node packages (if not already installed)
npm install

# Start Vite dev server on port 5173
npm --workspace apps/web run dev
```

The Web application is now live at:
- **Landing Page**: `http://127.0.0.1:5173/`
- **Demo Farm Direct**: `http://127.0.0.1:5173/demo`
- **Dashboard**: `http://127.0.0.1:5173/dashboard`

---

## 4. Production Build & Cloud Deployment

### Building Frontend for Production

```bash
npm run build:web
```
This generates static production assets in `apps/web/dist/` ready to be hosted on AWS S3/CloudFront, Vercel, or Netlify.

### Containerized Cloud Deployment (Docker)

To deploy the entire stack to any cloud container service (Render, Fly.io, AWS ECS, Google Cloud Run):

1. **Dockerfile for API**:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY . /app
   RUN pip install --no-cache-dir -e .
   EXPOSE 8000
   CMD ["python", "run_api.py"]
   ```

2. **Frontend Serving via Nginx**:
   ```dockerfile
   FROM nginx:alpine
   COPY apps/web/dist /usr/share/nginx/html
   EXPOSE 80
   CMD ["nginx", "-g", "daemon off;"]
   ```

---

## 5. Troubleshooting & Common Questions

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop'` | Windows asyncio default event loop | Run the backend using `python run_api.py`, which explicitly sets `loop_factory = lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())`. |
| `connection to server at "localhost", port 5432 failed` | Host port conflict or Docker not running | TerraPulse runs Docker PostGIS on port `5433` to prevent collision with native PostgreSQL installations. Ensure `.env` specifies `5433`. |
| Notifications not appearing during late evening testing | Quiet hours suppression policy (22:00–07:00 IST) | Use the `POST /api/v1/notifications/farms/{farm_id}/test` endpoint, which passes `ignore_quiet=True` to immediately dispatch test notifications. |
| Vite dev command fails with `--host` error | Command argument parsing | Host (`127.0.0.1`) and port (`5173`) are pre-configured in `apps/web/vite.config.ts`. Run `npm --workspace apps/web run dev`. |
| Missing `@react-three/fiber` or `three` | Dependencies not installed in root | Run `npm install` at the workspace root to install all workspace dependencies. |

