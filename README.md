# Activity Info Runner

A comprehensive platform for executing automated scripts and workflows against ActivityInfo databases. It leverages **Temporal** for robust workflow orchestration, providing reliable execution, retries, and comprehensive history tracking.

The system is designed to automate complex logic such as:
- **Calculation Formulas:** Applying Excel-like formulas to fields within or across forms.
- **Metric Configuration:** Managing the lifecycle of standardized metric fields.
- **Schema & Record Sync:** Calculating diffs between current and desired states and applying changes efficiently.

## Architecture

The project is built as a microservices architecture managed by Docker Compose:

*   **UI (Frontend):** A React-based dashboard (using BlueprintJS) to view available scripts, trigger runs, inspect execution logs, view changeset diffs (Database, Form, Field, Record), and analyze timing performance.
*   **Server (Backend):** A FastAPI service that acts as the gateway. It lists entities, starts Temporal workflows, and retrieves workflow status/history for the UI.
*   **Worker:** A Python Temporal Worker that executes the actual business logic (activities and workflows). It connects to ActivityInfo, processes data, and generates changesets.
*   **Temporal Server:** The core orchestration engine ensuring workflow reliability.
*   **PostgreSQL:** Persistence layer for Temporal.
*   **Redis:** Caching layer for API responses and blob storage for large payloads.

## Features

-   **Workflow Management:** Reliable execution of long-running scripts with automatic retries and failure handling.
-   **Plan/Apply Pattern:** Scripts first generate a "Materialized Boundary" (current state) and a "Desired Schema". The system then calculates a minimal "Changeset" (Diff) to transition the database to the desired state.
-   **Visual Diff:** The UI provides a detailed, color-coded diff view for all generated actions (Creates, Updates, Deletes) across Databases, Forms, Fields, and Records.
-   **Performance Analysis:** detailed timing charts breakdown the duration of every activity in a workflow run.
-   **Caching:** Intelligent caching of API responses and workflow results to optimize performance and reduce API load.
-   **Large Payload Support:** Uses a local blob store pattern to handle massive datasets that exceed standard RPC message limits.

## Prerequisites

-   **Docker** & **Docker Compose**
-   **ActivityInfo API Token** (for accessing your databases)

## Getting Started

### 1. Setup Environment

Create a `.env` file in the root directory:

```bash
# ActivityInfo API Token
API_TOKEN=your_secret_api_token_here

# Temporal & DB Config (Defaults usually fine for dev)
TEMPORAL_VERSION=1.29.1
TEMPORAL_ADMINTOOLS_VERSION=1.29.1-tctl-1.18.4-cli-1.5.0
POSTGRESQL_VERSION=16
POSTGRES_PASSWORD=temporal
POSTGRES_USER=temporal
```

### 2. Run the Stack

Start all services in detached mode:

```bash
docker-compose up --build -d
```

This will spin up:
- Temporal Server & Web UI (Port 8080)
- PostgreSQL & Redis
- AIR Server (API)
- AIR Worker
- AIR Frontend (UI)

### 3. Access the Dashboard

Open your browser and navigate to:

**http://localhost:8080**

From here you can:
1.  See a list of your ActivityInfo databases.
2.  Select a script to run (e.g., `OperationCalculationFormulas`).
3.  Click "Run script".
4.  Watch the workflow progress in real-time.
5.  Inspect the resulting Actions, Logs, and Timings.

## Development

### Project Structure

-   `api/`: FastAPI backend and ActivityInfo client.
-   `scripts/`: Contains the logic for specific scripts (e.g., `OperationCalculationFormulas`).
    -   `boundaries.py`: Logic to fetch the "Current State" (Materialization).
    -   `changeset.py`: Logic to compare states and generate actions.
    -   `models.py`: Pydantic models for the internal schema representation.
-   `ui/`: React frontend (Vite + BlueprintJS).
-   `worker.py`: Entry point for the Temporal Worker.
-   `server.py`: Entry point for the FastAPI Server.

### Running Locally (Without Docker for Worker/Server)

You can run the Python components locally against the Dockerized infrastructure (Temporal/Redis/PG) for faster dev cycles.

1.  **Start Infrastructure:**
    ```bash
    docker-compose up -d postgresql temporal temporal-admin-tools temporal-create-namespace redis
    ```
2.  **Install Dependencies:**
    ```bash
    uv sync
    ```
3.  **Run Worker:**
    ```bash
    source .venv/bin/activate
    python worker.py
    ```
4.  **Run Server:**
    ```bash
    source .venv/bin/activate
    uvicorn server:app --reload --port 8000
    ```
5.  **Run UI:**
    ```bash
    cd ui
    npm install
    npm run dev
    ```

## Scripts

### OperationCalculationFormulas

This script manages calculated fields based on a specific configuration form (`0.1.6`).
-   **Internal Calc:** Updates field formulas in the schema based on configuration.
-   **External Calc:** Fetches records, evaluates formulas locally using a custom parser, and updates the record values in ActivityInfo.

## Troubleshooting

-   **"Message larger than max"**: If you encounter this error, ensure the Blob Store volume is correctly mounted and the `blob_store.py` logic is being used for passing large datasets between activities.
-   **Worker not connecting**: Ensure `TEMPORAL_HOST` is set correctly in your `.env` or environment variables (default `localhost:7233` for local run, `temporal:7233` inside docker).
