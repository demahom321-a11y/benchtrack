
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from scalar_fastapi import (
    AgentScalarConfig,
    DocumentDownloadType,
    Layout,
    Theme,
    get_scalar_api_reference,
)

from app.routers.categories import router as categories_router
from app.routers.dashboard import router as dashboard_router
from app.routers.exports import router as exports_router
from app.routers.items import router as items_router
from app.routers.maintenance_tasks import (
    router as maintenance_tasks_router,
)
from app.routers.stock_movements import (
    router as stock_movements_router,
)

API_TAGS = [
    {"name": "System", "description": "Service health and availability."},
    {"name": "Dashboard", "description": "Workshop operational overview."},
    {"name": "Categories", "description": "Inventory category management."},
    {"name": "Items", "description": "Equipment and inventory management."},
    {"name": "Stock Movements", "description": "Inventory quantity changes."},
    {"name": "Maintenance", "description": "Workshop maintenance operations."},
    {"name": "Exports", "description": "CSV data exports."},
]


API_DESCRIPTION = """
## Overview

BenchTrack is a workshop inventory and maintenance management system
designed for small workshops.

The API provides structured endpoints for managing equipment,
inventory quantities, stock movements, categories and maintenance tasks.

## API Areas

Explore the available API modules:

- [System](#tag/system)
  Service health and availability.

- [Dashboard](#tag/dashboard)
  Inventory and operational statistics.

- [Categories](#tag/categories)
  Workshop equipment categories.

- [Items](#tag/items)
  Equipment records and stock information.

- [Stock Movements](#tag/stock-movements)
  Incoming, outgoing and adjustment operations.

- [Maintenance](#tag/maintenance)
  Maintenance tasks and scheduling.

- [Exports](#tag/exports)
  Download operational CSV reports.

## Stock movement rules

Inventory quantities are managed through stock movements:

| Type | Purpose |
| --- | --- |
| `IN` | Increase available stock |
| `OUT` | Decrease available stock |
| `ADJUSTMENT` | Set the actual stock quantity |

Direct quantity changes through ordinary item updates are not supported.

## Maintenance statuses

Maintenance tasks use the following statuses:

- `OPEN`
- `IN_PROGRESS`
- `COMPLETED`
- `CANCELLED`

Supported priorities are `LOW`, `MEDIUM` and `HIGH`.

## Response behavior

The API uses standard HTTP status codes and JSON responses for
operational endpoints. CSV export endpoints return downloadable files.

Validation errors are returned when submitted data does not satisfy
the request schema or business rules.

## Local development

The local API base URL is:

`http://127.0.0.1:8000`

Interactive documentation is available at `/docs`.
The alternative reference documentation is available at `/redoc`.
The machine-readable OpenAPI document is available at `/openapi.json`.

> This API currently does not implement user authentication.
"""


app = FastAPI(
    title="BenchTrack API",
    summary="Workshop Inventory & Maintenance Management",
    description=API_DESCRIPTION,
    version="0.1.0",
    openapi_tags=API_TAGS,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

templates = Jinja2Templates(directory="app/templates")


# API routers
app.include_router(categories_router)
app.include_router(items_router)
app.include_router(stock_movements_router)
app.include_router(maintenance_tasks_router)
app.include_router(dashboard_router)
app.include_router(exports_router)


# Main application page
@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="BenchTrack API | Developer Reference",
        theme=Theme.DEFAULT,
        layout=Layout.MODERN,
        dark_mode=False,
        hide_dark_mode_toggle=False,
        hide_search=False,
        hide_test_request_button=False,
        show_developer_tools="localhost",
        document_download_type=DocumentDownloadType.BOTH,
        order_required_properties_first=True,
        expand_all_model_sections=False,
        expand_all_responses=False,
        telemetry=False,
        agent=AgentScalarConfig(disabled=True),
        custom_css="""
            :root {
                --scalar-color-accent: #54766D;
                --scalar-background-1: #F3F4F1;
                --scalar-background-2: #FFFFFF;
                --scalar-background-3: #F0F2EF;
                --scalar-color-1: #293744;
                --scalar-color-2: #64717A;
                --scalar-border-color: #E3E6E2;
            }
            body {
                font-family: Inter, "Segoe UI", sans-serif;
            }
        """,
    )


@app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
async def custom_redoc():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#25394B">
        <title>BenchTrack API | Reference</title>
        <link rel="icon" type="image/svg+xml" href="/static/benchtrack-mark.svg">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
        <style>
            :root {
                color-scheme: light;
                --navy: #25394B;
                --green: #54766D;
                --canvas: #F3F4F1;
                --text: #293744;
                --muted: #78838A;
                --border: #E3E6E2;
            }

            * { box-sizing: border-box; }

            body {
                margin: 0;
                background: linear-gradient(180deg, #edf0ed 0%, #f7f8f5 100%);
                color: var(--text);
                font-family: "DM Sans", "Segoe UI", sans-serif;
            }

            .topbar {
                position: sticky;
                top: 0;
                z-index: 10;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 18px 32px;
                background: rgba(37, 57, 75, 0.96);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(255, 255, 255, 0.12);
                box-shadow: 0 16px 28px rgba(37, 57, 75, 0.08);
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 12px;
                color: #f7f9fb;
                text-decoration: none;
                font-family: "Manrope", "Segoe UI", sans-serif;
                font-weight: 800;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .brand-mark {
                width: 26px;
                height: 26px;
                display: block;
            }

            .topbar-badge {
                padding: 8px 12px;
                border-radius: 999px;
                border: 1px solid rgba(255,255,255,0.18);
                color: #edf6f3;
                background: rgba(84, 118, 109, 0.18);
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .page-shell {
                max-width: 1380px;
                margin: 32px auto 48px;
                padding: 0 20px;
            }

            .hero {
                display: grid;
                grid-template-columns: 1.2fr 0.8fr;
                gap: 24px;
                margin-bottom: 24px;
            }

            .hero-card,
            .example-card {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid var(--border);
                border-radius: 22px;
                box-shadow: 0 10px 30px rgba(37, 57, 75, 0.06);
            }

            .hero-card {
                padding: 28px 30px;
            }

            .eyebrow {
                margin: 0 0 10px;
                color: var(--green);
                font-size: 12px;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                font-weight: 800;
            }

            h1 {
                margin: 0;
                font-size: clamp(2.1rem, 3vw, 3rem);
                line-height: 1.1;
                font-family: "Manrope", "Segoe UI", sans-serif;
                color: var(--navy);
            }

            .hero-copy {
                margin-top: 14px;
                color: var(--muted);
                font-size: 1.02rem;
                line-height: 1.7;
                max-width: 64ch;
            }

            .meta-row {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-top: 24px;
            }

            .meta-pill {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 9px 12px;
                border-radius: 999px;
                background: #eef4f2;
                border: 1px solid #dfe8e5;
                color: var(--navy);
                font-size: 0.8rem;
                font-weight: 700;
            }

            .status-dot {
                width: 9px;
                height: 9px;
                border-radius: 50%;
                background: var(--green);
                display: inline-block;
            }

            .example-card {
                padding: 22px 20px 18px;
                background: #151d27;
                border-color: rgba(255,255,255,0.06);
                box-shadow: 0 20px 40px rgba(21, 29, 39, 0.22);
            }

            .example-card h2 {
                margin: 0 0 12px;
                color: #edf3f8;
                font-size: 0.82rem;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                font-family: "Manrope", "Segoe UI", sans-serif;
            }

            .code-block {
                background: #0d141a;
                border-radius: 16px;
                padding: 16px 18px;
                color: #d6eadf;
                border: 1px solid rgba(122, 166, 153, 0.18);
                font-family: "SFMono-Regular", Consolas, monospace;
                font-size: 0.82rem;
                line-height: 1.7;
                overflow: auto;
            }

            .code-block .token-key { color: #94d8bc; }
            .code-block .token-string { color: #f3d98b; }
            .code-block .token-number { color: #b7c8ff; }

            .content-grid {
                display: grid;
                grid-template-columns: 260px 1fr;
                gap: 24px;
            }

            .sidebar-panel {
                background: rgba(255,255,255,0.7);
                border: 1px solid var(--border);
                border-radius: 22px;
                padding: 20px 18px;
                box-shadow: 0 10px 26px rgba(37,57,75,0.04);
            }

            .sidebar-section {
                margin-bottom: 20px;
            }

            .sidebar-label {
                margin: 0 0 12px;
                color: var(--muted);
                font-size: 0.72rem;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                font-weight: 800;
            }

            .sidebar-list {
                list-style: none;
                margin: 0;
                padding: 0;
                display: grid;
                gap: 10px;
            }

            .sidebar-list li {
                padding: 10px 12px;
                border-radius: 12px;
                background: #f6f7f4;
                border: 1px solid #e9ece6;
                color: var(--text);
                font-weight: 600;
            }

            .panel {
                background: rgba(255,255,255,0.74);
                border: 1px solid var(--border);
                border-radius: 22px;
                padding: 24px 22px;
                box-shadow: 0 10px 26px rgba(37,57,75,0.04);
            }

            .panel h3 {
                margin: 0 0 18px;
                color: var(--navy);
                font-family: "Manrope", "Segoe UI", sans-serif;
                font-size: 1.2rem;
            }

            .feature-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 16px;
            }

            .feature-card {
                padding: 16px 18px;
                border: 1px solid var(--border);
                border-radius: 18px;
                background: linear-gradient(180deg, rgba(84,118,109,0.05), rgba(255,255,255,0.5));
            }

            .feature-card strong {
                display: block;
                margin-bottom: 8px;
                color: var(--navy);
                font-size: 0.92rem;
            }

            .feature-card span {
                color: var(--muted);
                line-height: 1.6;
                font-size: 0.95rem;
            }

            @media (max-width: 900px) {
                .hero,
                .content-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <header class="topbar">
            <div class="brand">
                <img class="brand-mark" src="/static/benchtrack-mark.svg" alt="BenchTrack">
                <span>BenchTrack API</span>
            </div>
            <div class="topbar-badge">Reference</div>
        </header>

        <main class="page-shell">
            <section class="hero">
                <div class="hero-card">
                    <p class="eyebrow">Workshop operations</p>
                    <h1>Developer reference</h1>
                    <div class="hero-copy">
                        BenchTrack exposes a structured REST surface for inventory, stock movement tracking,
                        category management and maintenance operations. This reference is designed for quick
                        inspection, testing and integration with workshop tooling.
                    </div>
                    <div class="meta-row">
                        <span class="meta-pill"><span class="status-dot"></span> Healthy</span>
                        <span class="meta-pill">OpenAPI v3</span>
                        <span class="meta-pill">Local server</span>
                    </div>
                </div>

                <aside class="example-card">
                    <h2>Example payload</h2>
                    <pre class="code-block"><span class="token-key">POST</span> /items
{
  <span class="token-key">"name"</span>: <span class="token-string">"Angle grinder"</span>,
  <span class="token-key">"sku"</span>: <span class="token-string">"GR-1001"</span>,
  <span class="token-key">"category_id"</span>: <span class="token-number">2</span>,
  <span class="token-key">"minimum_stock"</span>: <span class="token-number">3</span>,
  <span class="token-key">"location"</span>: <span class="token-string">"Bay A"</span>
}</pre>
                </aside>
            </section>

            <section class="content-grid">
                <aside class="sidebar-panel">
                    <div class="sidebar-section">
                        <p class="sidebar-label">API areas</p>
                        <ul class="sidebar-list">
                            <li>System</li>
                            <li>Dashboard</li>
                            <li>Categories</li>
                            <li>Items</li>
                            <li>Stock Movements</li>
                            <li>Maintenance</li>
                            <li>Exports</li>
                        </ul>
                    </div>
                </aside>

                <div class="panel">
                    <h3>Reference highlights</h3>
                    <div class="feature-grid">
                        <div class="feature-card">
                            <strong>Inventory</strong>
                            <span>Track equipment, stock thresholds and storage locations with clear state transitions.</span>
                        </div>
                        <div class="feature-card">
                            <strong>Movements</strong>
                            <span>Capture stock IN, OUT and adjustment actions to maintain accurate quantity history.</span>
                        </div>
                        <div class="feature-card">
                            <strong>Maintenance</strong>
                            <span>Manage scheduled tasks, priorities and completion states across workshop assets.</span>
                        </div>
                        <div class="feature-card">
                            <strong>Exports</strong>
                            <span>Generate CSV exports for the operational records used by staff and supervisors.</span>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    </body>
    </html>
    """


# System health endpoint
@app.get(
    "/health",
    tags=["System"],
    summary="Check API health",
    description=(
        "Returns the current basic health status of the BenchTrack API service."
    ),
)
def health_check():
    return {
        "status": "healthy",
    }
