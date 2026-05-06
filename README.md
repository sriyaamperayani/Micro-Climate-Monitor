# Micro Climate Monitor

FastAPI-based micro climate monitoring service with:
- sensor data ingestion APIs
- in-memory rolling storage
- anomaly detection
- Loki log shipping
- Grafana dashboards
- background sensor simulation
- pytest tests

## Features

- `POST /readings` to ingest environmental sensor readings (`temperature`, `humidity`, `pressure`).
- `GET /readings` to fetch stored readings as JSON.
- `GET /anomalies` to detect outliers where any metric is beyond 2 standard deviations from mean.
- In-memory storage uses `deque(maxlen=1000)`, so only the latest 1000 readings are kept.
- Background task generates simulated readings every 5 seconds.
- Structured logging with `python-loki-logger`, forwarded to Loki.
- Grafana + Loki stack via Docker Compose.
- Provisioned Grafana datasource and dashboard for temperature/humidity/pressure + logs.
- Unit tests with `pytest` and FastAPI `TestClient`.

## Tech Stack

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- python-loki-logger
- Grafana
- Loki
- Docker Compose
- pytest

## Project Structure

```text
micro-climate-monitor/
├── main.py
├── test_main.py
├── requirements.txt
├── docker-compose.yml
├── loki-config.yml
├── .env.example
├── .gitignore
└── grafana/
    ├── dashboards/
    │   └── micro-climate-overview.json
    └── provisioning/
        ├── dashboards/
        │   └── dashboard.yml
        └── datasources/
            └── datasource.yml
```

## Prerequisites

- Python 3.12+
- Docker Desktop (running)
- macOS/Linux shell (commands below use bash/zsh style)

## Local Setup

1. Clone repository and enter project:
```bash
git clone <your-repo-url>
cd micro-climate-monitor
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4. (Optional) Create `.env` from template:
```bash
cp .env.example .env
```

## Run the Project

### 1) Start Grafana + Loki

```bash
docker compose up -d
```

- Grafana: `http://localhost:3000`
- Loki: `http://localhost:3100`

### 2) Start FastAPI app

```bash
uvicorn main:app --reload
```

- API docs: `http://127.0.0.1:8000/docs`

## API Endpoints

### `POST /readings`

Request example:
```bash
curl -X POST "http://127.0.0.1:8000/readings" \
  -H "Content-Type: application/json" \
  -d '{"temperature":22.5,"humidity":45.2,"pressure":1013.2}'
```

### `GET /readings`

```bash
curl "http://127.0.0.1:8000/readings"
```

### `GET /anomalies`

Returns readings where one or more fields are > 2 standard deviations from the mean.

```bash
curl "http://127.0.0.1:8000/anomalies"
```

Sample anomaly response item:
```json
{
  "temperature": 40.5,
  "humidity": 20.1,
  "pressure": 1040.7,
  "timestamp": "2026-05-06T09:00:00.000000",
  "reason": "temperature, pressure"
}
```

## Observability (Grafana + Loki)

- Logs are pushed from app to Loki with labels:
  - `app="micro-climate-monitor"`
  - `service="api"`
- Grafana datasource is provisioned automatically.
- Dashboard is provisioned automatically: `Micro Climate Overview`
  - Temperature panel
  - Humidity panel
  - Pressure panel
  - Sensor logs panel (JSON)

If dashboards or datasource do not appear after changes:
```bash
docker compose restart grafana
```

## Run Tests

```bash
python -m pytest -q
```

Current tests in `test_main.py`:
- POST `/readings` returns `200`
- POST response includes `temperature`, `humidity`, `pressure`, `timestamp`
- GET `/readings` returns a list

## Screenshot Checklist (Feature-by-Feature)

Add one screenshot for each feature below:

1. FastAPI docs page at `/docs`
2. Successful `POST /readings` request in terminal or Swagger
3. `GET /readings` showing stored list
4. `GET /anomalies` output example
5. Background simulator logs updating every ~5 seconds
6. Grafana Explore query showing Loki logs
7. Grafana dashboard with temperature chart
8. Grafana dashboard with humidity chart
9. Grafana dashboard with pressure chart
10. Grafana logs panel with structured JSON entries
11. `pytest` output showing all tests passed

## Security Notes

- Environment variables like `GRAFANA_USER`, `GRAFANA_PASSWORD`, and `LOKI_URL` should be kept in local environment files and never committed to source control.
- Grafana's default `admin/admin` credentials are only acceptable for local development and must be changed in production.
- For production deployments, manage secrets using a dedicated secrets manager such as [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) or [HashiCorp Vault](https://www.vaultproject.io/).

## Known Limitations

- Data storage is in-memory only (not persistent across app restarts).
- Background simulator runs in-process (single app instance assumptions).
- `@app.on_event` emits deprecation warnings in latest FastAPI (can be migrated to lifespan handler later).

## GitHub Upload (First Time)

If this folder is not yet a git repo:

```bash
git init
git add .
git commit -m "Initial micro climate monitor app with Grafana and Loki"
```

Create a GitHub repo (web UI), then connect and push:

```bash
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
