# Client Report — AI Construction Estimator
**Prepared for:** Melvin Guzman — Mel's Builders Pro Systems  
**Prepared by:** Atul (development team)  
**Date:** May 21, 2026  

---

## What We Built

- A web application that accepts structural PDF plan sets and automatically extracts construction data using AI (GPT-4o)
- You upload a PDF, the AI reads it, and you get a downloadable PDF report with all the extracted specs and connection details
- Built with a professional black and yellow theme matching your brand

---

## What It Does Right Now (V1)

- **Upload any structural PDF** — drag and drop or click to browse
- **AI reads the plans automatically** — no manual data entry
- **Live progress bar** — shows you exactly what the AI is doing while it processes
- **Extracts the following from structural plan sets:**
  - Concrete specs (PSI ratings, mix design, rebar development lengths)
  - Lumber specs (LVL, LSL, PSL, GLB — grades and design values)
  - Nailing schedules
  - Simpson hardware model numbers
  - Framing connection details (what connects to what, what fastener to use)
  - Sheet list (all structural sheets in the set)
  - Project info (name, address, architect, structural engineer)
- **Generates a PDF report** you can download and save
- **Dashboard** — see all your past jobs in one place
- **Delete jobs** you no longer need

---

## What It Does NOT Do (yet — V2 roadmap)

- **Does not calculate concrete cubic yards** — those numbers come from graphical drawings (dimension lines), not the text layer. AI can estimate but numbers are not reliable enough for ordering.
- **Does not calculate linear feet** of rebar or footings — same reason
- **Does not count lumber pieces** (e.g. "how many 2×10s") — requires reading framing plan geometry
- **Does not generate labor estimates, equipment costs, or schedules** — these are not in the PDF; need to be calculated from quantities
- **Does not support scanned/stamped PDFs** — V1 is for digital PDFs only. Scanned plans require a separate pipeline (built and tested but not wired into the web app yet)

---

## Tested On — 6 Real Plan Sets

| Plan Set | Pages | Result |
|---|---|---|
| SVR 80% CD Set | 27 relevant / 167 total | ✅ 52 Simpson items, 49 connections, 11 nailing entries |
| Whaleon Residence CD | 7 relevant / 73 total | ✅ Foundation footings, rebar, 12 hardware items |
| BARAGHOUSH DD | 0 relevant / 17 total | ✅ Correctly identified as architectural-only (no SE work yet) |
| Paseo Miramar RTI (scanned) | 37 relevant / 57 total | ✅ Raster pipeline validated separately |
| 4248 Woodlane Court | 5 relevant / 60 total | ✅ 4 steel moment frame connections |
| LHERT SONG CD Bid Set | 10 relevant / 64 total | ✅ 43 framing connections, concrete + lumber specs |

---

## How to Start the App

**Step 1 — Make sure Docker Desktop is running**

**Step 2 — Open a terminal, go to the app folder:**
```
cd /home/lap-68/Documents/gt-atul/atul-melvin-architecture-analysis-and-analysis/app
```

**Step 3 — Start everything:**
```
docker compose up -d
```

**Step 4 — First time only — run database setup:**
```
docker compose exec backend python -m alembic upgrade head
```

**Step 5 — Open the app in your browser:**
```
http://localhost:3036
```

**Step 6 — To stop the app:**
```
docker compose down
```

---

## Login Credentials

| Field | Value |
|---|---|
| Username | `smoketest` |
| Password | `smoketest123` |

> **Important:** There is no "Sign Up" button in V1. To create a new user, the developer needs to run a command. We recommend creating a proper username/password for Melvin before go-live.

**To create a new user (developer runs this):**
```bash
docker compose exec backend python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.auth import create_user
async def main():
    async with AsyncSessionLocal() as db:
        await create_user(db, 'melvin', 'YOUR_PASSWORD_HERE')
        await db.commit()
asyncio.run(main())
"
```

---

## Ports (where each service runs)

| Service | Address |
|---|---|
| Web app (frontend) | http://localhost:3036 |
| API (backend) | http://localhost:8037 |
| Database (PostgreSQL) | localhost:5039 |

---

## Environment File — Required Keys

The app needs a file called `.env` inside the `app/` folder. It must contain:

```
POSTGRES_USER=estimator
POSTGRES_PASSWORD=your-database-password
POSTGRES_DB=estimator_db
SECRET_KEY=a-random-64-character-string
OPENAI_API_KEY=sk-your-openai-key-here
```

| Key | What It Is | Where to Get It |
|---|---|---|
| `POSTGRES_USER` | Database username | You choose — set once and keep it |
| `POSTGRES_PASSWORD` | Database password | You choose — make it strong |
| `POSTGRES_DB` | Database name | You choose — `estimator_db` is fine |
| `SECRET_KEY` | Used to sign login tokens | Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `OPENAI_API_KEY` | Your OpenAI API key | https://platform.openai.com/api-keys |

> **Never share this file or commit it to GitHub.** It is listed in `.gitignore` and will not be included in any code backup.

---

## OpenAI API — Costs

- The AI uses **GPT-4o** to read each structural page
- Cost is per page processed, not per upload
- Typical costs from testing:
  - Small set (7 pages): ~$0.07
  - Medium set (10 pages): ~$0.28
  - Large set (27 pages): ~$0.00 (text-only pages are very cheap)
- **Scanned PDFs cost more** — Vision processing is more expensive than text extraction
- You can monitor usage and set spending limits at https://platform.openai.com/usage

---

## Known Issues (to fix in next round)

1. **Project name / address / SE sometimes not extracted** — seen on Ashley & Vance (LHERT SONG) plan sets. The title block format for that firm is handled differently. Fix is identified, not yet applied to the web app. Workaround: project name is entered manually when uploading.

2. **Foundation quantities = 0** on graphical foundation plans — this is expected. The AI reads the dimension labels when they exist in the text layer, but most firms draw the footing layout graphically. AI estimates vary run-to-run and are not reliable for ordering.

3. **No self-service registration** — need developer to create users. Simple to add in V2.

4. **Scanned PDFs not supported** in V1 web app — digital PDFs only. The raster pipeline exists as a separate script and can be integrated in V2.

---

## What's Coming in V2 (proposed)

- **Quantity takeoff module** — attempt to extract concrete CY, rebar LF, lumber piece counts from graphical drawings (R&D work, 4–6 weeks, accuracy not guaranteed)
- **User registration** — self-service signup
- **Scanned PDF support** — integrate the raster pipeline into the web app
- **Better project info extraction** — fix Pattern 5 (Ashley & Vance title block) in web app
- **Multiple users / team accounts**

---

## File Locations

| Item | Location |
|---|---|
| App source code | `app/` |
| Environment file | `app/.env` (you create this — never commit) |
| Environment template | `app/.env.example` |
| Backend API code | `app/backend/app/` |
| Frontend code | `app/frontend/src/` |
| Docker compose | `app/docker-compose.yml` |
| Test PDFs | `~/Downloads/` (on dev machine) |
| Test results (known-good) | `output/` |
| Pipeline research docs | `docs/pipeline-findings.md` |
| Architecture design spec | `docs/superpowers/specs/2026-05-20-ai-construction-estimator-design.md` |
| Implementation plan | `docs/superpowers/plans/2026-05-21-web-app.md` |

---

## Quick Reference Card

| Task | Command |
|---|---|
| Start app | `cd app && docker compose up -d` |
| Stop app | `cd app && docker compose down` |
| View logs | `docker compose logs -f backend` |
| Run DB migration | `docker compose exec backend python -m alembic upgrade head` |
| Create new user | See "Login Credentials" section above |
| Check containers | `docker compose ps` |
| Restart backend only | `docker compose restart backend` |

---

*Questions or issues — contact Atul.*
