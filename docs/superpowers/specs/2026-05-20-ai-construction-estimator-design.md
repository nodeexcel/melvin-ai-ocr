# AI Construction Estimator — Design Spec

**Date:** 2026-05-20  
**Client:** Melvin Guzman (Mel's Builders Pro Systems)  
**Status:** Draft

---

## Overview

An AI-powered web application that accepts architectural/construction PDF plan sets, analyzes them using Claude Vision API, and generates detailed construction material takeoff estimates. Results are displayed live with streaming progress and exportable as a branded PDF report.

---

## Decisions & Constraints

| Decision | Choice | Notes |
|---|---|---|
| Users | Single user (Melvin) | Expandable to multi-user later |
| Platform | Hosted web app | Docker-based deployment |
| Processing time | 5–10 min acceptable | With live progress stream |
| Output | View on screen + PDF export + project history | No Excel for now |
| Auth | JWT + username/password | No self-signup, account created manually |
| Containerization | Docker + docker-compose | Single `docker compose up` to run |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL |
| ORM | SQLAlchemy (async) + Alembic |
| PDF → images | `pdf2image` + `poppler` |
| AI Vision | Claude API — `claude-sonnet-4-5` |
| Output PDF | `reportlab` |
| Auth | JWT (`python-jose`) + `bcrypt` |
| File storage | Docker volume (local disk) |
| Orchestration | `docker-compose` |

---

## Ports

| Service | Port |
|---|---|
| Frontend (Next.js) | 3036 |
| Backend (FastAPI) | 8037 |
| Database (PostgreSQL) | 5039 |

---

## Core Processing Pipeline

```
1.  User uploads PDF
        ↓
2.  Backend creates project record (status: pending)
        ↓
3.  ProcessPoolExecutor offloads CPU work:
    - Convert PDF pages → images (pdf2image + poppler)
        ↓
4.  Identify relevant sheet types per page:
    - Structural (S-series): framing plans, beam schedules
    - Architectural (A-series): floor plans, area calculations
    - General notes (T-series): material specs, code requirements
        ↓
5.  Send each relevant page image to Claude Vision API
    with a targeted prompt per sheet type
        ↓
6.  Parse Claude's response → structured JSON
        ↓
7.  After each step, write progress event to DB (job_events table)
        ↓
8.  SSE endpoint polls DB every 500ms → streams events to browser
        ↓
9.  On completion: aggregate all extracted data → final JSON result
        ↓
10. Generate PDF report (reportlab) branded as Mel's Builders Pro Systems
        ↓
11. Save project as completed, report path stored in DB
```

**Why ProcessPoolExecutor over Celery/Redis:**  
PDF rendering is CPU-bound and blocks the async event loop. ProcessPoolExecutor offloads to separate OS processes, keeping FastAPI responsive. For one user at this scale, no task queue infrastructure is needed. Upgrade to Celery + Redis only when concurrency or scale demands it.

**Why DB-backed progress over in-memory queues:**  
Worker processes share no memory with the FastAPI process. Writing progress to PostgreSQL is the simplest reliable bridge — no IPC complexity, survives restarts, and reuses existing infrastructure.

---

## Data Models

### `users`
```
id              UUID, primary key
username        VARCHAR, unique, not null
hashed_password VARCHAR, not null
created_at      TIMESTAMP, default now()
```

### `projects`
```
id                UUID, primary key
user_id           UUID, foreign key → users.id
name              VARCHAR (project name)
original_filename VARCHAR (uploaded file name)
file_path         VARCHAR (path to stored PDF)
status            ENUM: pending | processing | done | failed
created_at        TIMESTAMP, default now()
completed_at      TIMESTAMP, nullable
```

### `job_events`
```
id           SERIAL, primary key
project_id   UUID, foreign key → projects.id
step         VARCHAR  (e.g. "rendering", "analyzing", "generating_report")
message      TEXT     (human-readable, shown in UI progress feed)
progress_pct INTEGER  (0–100)
created_at   TIMESTAMP, default now()
```

### `analysis_results`
```
id              UUID, primary key
project_id      UUID, foreign key → projects.id
raw_json        JSONB  (full structured output from Claude)
report_pdf_path VARCHAR (path to generated PDF)
created_at      TIMESTAMP, default now()
```

---

## API Endpoints

### Auth
```
POST /api/auth/login
  Body: { username, password }
  Returns: { access_token, token_type }
```

### Projects
```
POST /api/projects/upload
  Auth: Bearer JWT
  Body: multipart/form-data (pdf file + project name)
  Returns: { project_id, status }
  Action: saves file, creates project record, starts background processing

GET /api/projects
  Auth: Bearer JWT
  Returns: list of all projects with status and metadata

GET /api/projects/{id}
  Auth: Bearer JWT
  Returns: project details + analysis results (if done)

DELETE /api/projects/{id}
  Auth: Bearer JWT
  Action: deletes project, associated events, results, and files
```

### SSE Progress Stream
```
GET /api/projects/{id}/stream
  Auth: Bearer JWT
  Returns: text/event-stream
  Behavior: polls job_events table every 500ms, pushes new events to client
            closes stream when project status = done | failed
  Event format:
    data: { step, message, progress_pct, timestamp }
```

### Report
```
GET /api/projects/{id}/report
  Auth: Bearer JWT
  Returns: application/pdf (file download)
```

---

## Analysis Output Structure (raw_json)

Claude's output is parsed into this structure and stored in `analysis_results.raw_json`:

```json
{
  "project": {
    "name": "San Vicente Residence",
    "address": "12957 San Vicente Blvd, Los Angeles, CA 90049",
    "architect": "BSPK Design",
    "total_sqft": 0
  },
  "foundation": {
    "concrete_cubic_yards": 0,
    "rebar_lf": 0,
    "rebar_qty": 0,
    "notes": []
  },
  "floor_framing": {
    "lumber": [],
    "hardware": []
  },
  "wall_framing": {
    "lumber": [],
    "sheathing_sheets": 0,
    "hardware": []
  },
  "roof_framing": {
    "lumber": [],
    "sheathing_sheets": 0,
    "hardware": []
  },
  "simpson_hardware": [],
  "labor_estimate": {},
  "equipment_costs": {},
  "waste_factors": {},
  "procurement_list": [],
  "construction_schedule": []
}
```

---

## UI Design

- **Color scheme:** Black and yellow (Mel's Builders Pro Systems brand)
- **Key screens:**
  1. Login page
  2. Dashboard — project history list
  3. Upload page — drag & drop PDF
  4. Progress page — live SSE stream with step-by-step feed
  5. Results page — structured estimate display
  6. Report download button

---

## PDF Report Branding

```
Company: Mel's Builders Pro Systems
Tagline:  "On Time, On Budget, Beyond Expectations."
Colors:   Black and yellow
```

---

## What's Explicitly Out of Scope (for now)

- Multi-user / team accounts
- Excel export
- Email notifications
- Mobile app
- Third-party integrations (Procore, Buildertrend, etc.)
- Cloud file storage (S3)
- Celery / Redis task queue
