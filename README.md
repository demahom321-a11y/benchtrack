# BenchTrack

[![CI](https://github.com/demahom321-a11y/benchtrack/actions/workflows/ci.yml/badge.svg)](https://github.com/demahom321-a11y/benchtrack/actions/workflows/ci.yml)

**Workshop Inventory and Maintenance Management System**

BenchTrack is a backend-focused web application for managing workshop equipment, inventory levels, stock movements, and maintenance operations. It provides a structured API, transactional stock updates, searchable records, operational summaries, and CSV exports.

The project demonstrates practical application development with Python, FastAPI, SQLAlchemy, SQLite, database migrations, automated testing, and API documentation.

## Core Capabilities

### Inventory Management

- Create, retrieve, update, and delete equipment records.
- Organize equipment into categories.
- Track current quantities, minimum stock levels, and storage locations.
- Search, filter, sort, and paginate inventory records.
- Prevent ordinary item updates from directly modifying stock quantities.
- Protect records with existing operational history from unsupported deletion.

### Stock Movement Management

- Record incoming stock movements (`IN`).
- Record outgoing stock movements (`OUT`).
- Record stock adjustments (`ADJUSTMENT`) using the actual counted quantity.
- Reject outgoing movements that exceed available stock.
- Preserve movement records with previous and resulting stock quantities.
- Use SQLite's `BEGIN IMMEDIATE` transaction mode before reading and updating stock quantities, helping prevent concurrent movements from acting on the same outdated stock value.

### Maintenance Management

- Create, retrieve, update, and delete maintenance tasks.
- Associate maintenance tasks with inventory items.
- Track task statuses: `OPEN`, `IN_PROGRESS`, `COMPLETED`, and `CANCELLED`.
- Set priorities: `LOW`, `MEDIUM`, and `HIGH`.
- Track scheduled dates and completion timestamps.
- Search, filter, sort, and paginate maintenance records.

### Dashboard and Data Exports

- Retrieve inventory and operational summaries.
- Review stock and maintenance activity.
- Export inventory, stock movements, and maintenance tasks as CSV files.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Language | Python |
| Backend framework | FastAPI |
| Data validation and serialization | Pydantic |
| ORM | SQLAlchemy |
| Database | SQLite |
| Schema migrations | Alembic |
| API specification | OpenAPI |
| Interactive API reference | Scalar |
| Alternative API documentation | ReDoc |
| Server-side templates | Jinja2 |
| Frontend | HTML, CSS, JavaScript |
| Automated testing | pytest, FastAPI TestClient |
| Test HTTP dependency | httpx2 |
| Linting | Ruff |
| Continuous integration | GitHub Actions |

## Application Structure

The application separates HTTP routing, request and response schemas, database models, and frontend resources.

```text
benchtrack/
|-- app/
|   |-- models/
|   |-- routers/
|   |-- schemas/
|   |-- static/
|   |-- templates/
|   |-- database.py
|   `-- main.py
|-- migrations/
|   `-- versions/
|-- tests/
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- alembic.ini
|-- pyproject.toml
`-- README.md
```

**Application responsibilities**

- `app/routers/`: API route handlers and HTTP-level behavior.
- `app/schemas/`: request validation and response serialization.
- `app/models/`: SQLAlchemy database models.
- `app/database.py`: database engine, session configuration, and dependency management.
- `app/templates/` and `app/static/`: web interface templates and frontend assets.
- `migrations/`: version-controlled database schema changes.
- `tests/`: automated tests using isolated test database sessions.

## API Reference

BenchTrack exposes the following HTTP operations.

| Resource | Method | Endpoint | Purpose |
| --- | --- | --- | --- |
| System | GET | `/health` | Health check |
| Dashboard | GET | `/dashboard/` | Operational summaries |
| Categories | GET | `/categories/` | List categories |
| Categories | POST | `/categories/` | Create a category |
| Categories | GET | `/categories/{category_id}` | Retrieve a category |
| Categories | PATCH | `/categories/{category_id}` | Update a category |
| Categories | DELETE | `/categories/{category_id}` | Delete a category |
| Items | POST | `/items/` | Create an inventory item |
| Items | GET | `/items/` | List and filter inventory items |
| Items | GET | `/items/{item_id}` | Retrieve an item |
| Items | PATCH | `/items/{item_id}` | Update an item |
| Items | DELETE | `/items/{item_id}` | Delete an item |
| Stock movements | POST | `/items/{item_id}/movements/` | Record an item stock movement |
| Stock movements | GET | `/items/{item_id}/movements/` | Retrieve an item's movement history |
| Stock movements | GET | `/stock-movements/` | List and filter stock movements |
| Maintenance | POST | `/maintenance-tasks/` | Create a maintenance task |
| Maintenance | GET | `/maintenance-tasks/` | List and filter maintenance tasks |
| Maintenance | GET | `/maintenance-tasks/{task_id}` | Retrieve a maintenance task |
| Maintenance | PATCH | `/maintenance-tasks/{task_id}` | Update a maintenance task |
| Maintenance | DELETE | `/maintenance-tasks/{task_id}` | Delete a maintenance task |
| Exports | GET | `/exports/items.csv` | Export inventory records |
| Exports | GET | `/exports/stock-movements.csv` | Export stock movement records |
| Exports | GET | `/exports/maintenance-tasks.csv` | Export maintenance records |

### Interactive API Documentation

FastAPI generates the OpenAPI specification from the application's routes, schemas, and validation definitions.

The project provides the following local documentation endpoints:

| Resource | URL |
| --- | --- |
| Scalar API reference | `/docs` |
| ReDoc API reference | `/redoc` |
| OpenAPI specification | `/openapi.json` |

The Scalar interface allows developers to explore endpoints, inspect request and response schemas, review documented HTTP status codes, and send test requests to the local application.

## Requirements

- Python 3.11 or newer.
- pip.
- Git.

The project has been tested locally with Python 3.13.

## Installation

Clone the repository:

```bash
git clone https://github.com/demahom321-a11y/benchtrack.git
cd benchtrack
```

Create a virtual environment:

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux and macOS**

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the application and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Database Setup

BenchTrack uses SQLite by default.

Apply the existing database migrations:

```bash
alembic upgrade head
```

The default database URL is:

```text
sqlite:///./benchtrack.db
```

The local SQLite database is excluded from version control.

## Running the Application

Start the development server:

```bash
uvicorn app.main:app --reload
```

Open the application in your browser:

- Web application: `http://127.0.0.1:8000`
- Scalar API reference: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI specification: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

## Testing and Code Quality

Run the automated test suite:

```bash
python -m pytest -q
```

Run Ruff:

```bash
python -m ruff check app tests
```

Check installed dependency consistency:

```bash
python -m pip check
```

The test suite uses isolated database sessions rather than the local application database, helping prevent test execution from modifying local application data.

## Database Migrations

Inspect the currently applied migration revision:

```bash
alembic current
```

Inspect migration history:

```bash
alembic history
```

After an intentional database schema change, generate a migration:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

Review every generated migration before applying it. Autogenerated migrations should not be treated as automatically correct.

Apply reviewed migrations with:

```bash
alembic upgrade head
```

## Continuous Integration

The GitHub Actions workflow is configured to run on:

- Pushes to the `main` branch.
- Pull requests targeting the `main` branch.

The workflow:

1. Checks out the repository.
2. Sets up Python 3.13.
3. Installs the project and development dependencies.
4. Runs Ruff against the application and test code.
5. Executes the pytest test suite.

This provides an automated quality check for repository changes.

## Security and Scope

BenchTrack does not currently implement user authentication or authorization.

The application is intended for local development, demonstration, and technical evaluation. It should not be exposed to untrusted networks or deployed as a publicly accessible service without appropriate security controls.

Authentication, authorization, and deployment security requirements remain outside the current project scope.

Local database files, virtual environments, and environment configuration files are excluded from version control.

## Project Status

The current implementation includes inventory management, stock movement processing, maintenance workflows, dashboard summaries, CSV exports, database migrations, automated tests, and interactive API documentation.

The repository is maintained as a technical portfolio project, with an emphasis on backend implementation, data integrity, API design, testing, and code quality.
