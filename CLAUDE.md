# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

AutoApply (jobless.io) is a local AI-powered job application automation platform. It takes a user's `data/profile.json`, discovers LinkedIn job listings via Playwright scraping, generates hyper-tailored CVs/cover letters via a GAN-style LLM loop, auto-applies via Playwright (LinkedIn Easy Apply) or Brevo SMTP, and provides a persona-driven interview simulator. All state is stored as local JSON — no database.

The primary user profile is at `data/profile.json`.

---

## Running the Project

**Prerequisites:** Python 3.11+, Node 18+, Playwright Chromium installed.

```bash
# 1. Copy .env.example → .env and populate API keys:
#    GROQ_API_KEY, APIFY_TOKEN, BREVO_SMTP_PASSWORD, LINKEDIN_EMAIL, LINKEDIN_PASSWORD, OPENROUTER_API_KEY

# 2. Backend (venv recommended)
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium
uvicorn backend.main:app --reload   # http://localhost:8000

# 3. Frontend
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

Both servers must run concurrently. Vite is configured for port **3000** (`vite.config.js`), and FastAPI CORS allows `http://localhost:3000`.

---

## Running Tests

```bash
# All tests
pytest tests/

# Single test file
pytest tests/test_cv_service.py -v

# Single test function
pytest tests/test_discovery.py::test_suggest_roles -v
```

Tests use `unittest.mock` to patch Groq/Apify calls. Never hit live APIs in tests. Test fixtures that write files use `tempfile.TemporaryDirectory` and patch `settings.DATA_DIR`.

---

## Architecture: Data Flow

```
data/profile.json
    │
    ▼  (Phase 2 - Discovery)
Groq → role suggestions → user picks → Playwright scrapes LinkedIn jobs
    │
    ▼
data/targets.json  [list of TargetCompany]
    │
    ▼  (Phase 3 - Research)
Scrapes job posting text → Groq synthesizes HiringPersona
    │
    ▼
data/applications/{company_id}/meta.json
    │
    ▼  (Phase 4 - GAN Loop)
Groq B (Generator) ⟷ Groq A (Discriminator as HR) → max iterations → score ≥ MIN_CV_SCORE
    │
    ▼
data/applications/{company_id}/cv.json + cv.pdf + cover_letter.pdf
    │
    ▼  (Phase 5 - Apply)
Playwright Easy Apply  OR  Brevo SMTP email + LinkedIn DM
    │
    ▼
data/history.json
    │
    ▼  (Phase 7 - Interview)
Groq role-plays as HR persona → score transcript → save to data/interview_sessions/{company_id}/
```

---

## Backend Architecture

**Stack:** FastAPI + Pydantic v2 + Python 3.11+

**Entry point:** `backend/main.py` — mounts routers, configures CORS, global exception handler. Sets `WindowsProactorEventLoopPolicy` on Windows for Playwright compatibility.

**Config:** `backend/config.py` — `Settings` (pydantic-settings). All file paths, API keys, and behavioral constants live here. Current values: `MAX_GAN_ITERATIONS=2`, `MIN_CV_SCORE=7.5`, `MAX_DAILY_APPLICATIONS=20`.

**Routers → Services pattern:**
- `backend/routers/` — thin HTTP layer, delegates to services
  - `discovery.py` — `/api/discovery`: role suggestions, LinkedIn scraping, target management
  - `generation.py` — `/api/generation`: CV/cover letter generation with SSE progress streaming
  - `apply.py` — `/api/apply`: sequential application execution with daily rate limiting
  - `interview.py` — `/api/interview`: session start/message/help/end endpoints
  - `profile.py` — `/api/profile`: profile read/update/completeness
  - `history.py` — `/api/history`: application history management

- `backend/services/` — business logic:
  - `groq_service.py` — wraps OpenRouter API (OpenAI-compatible) via `httpx.AsyncClient`. The only LLM entry point: `await call_groq(system_prompt, user_message, expect_json, purpose)`. Falls back to hardcoded mock responses when `OPENROUTER_API_KEY` is unset, keyed by `purpose` prefix (`"generate_"`, `"score_"`, `"synthesize_persona"`, `"suggest_roles"`). Also exports `_log_groq_decision()` for structured logging.
  - `cv_service.py` — orchestrates `research_company()` → `run_gan_loop()` → `render_cv_to_pdf()`. The GAN loop is the core generation engine. `render_cv_to_pdf()` uses **inline Jinja2 template strings** (`_CV_TEMPLATE`, `_CL_TEMPLATE` constants, not external files) rendered via `sync_playwright` in a thread executor.
  - `apify_service.py` — uses Playwright to scrape LinkedIn jobs/company profiles. Falls back to mock data on any scraping failure (not dependent on `APIFY_TOKEN`).
  - `playwright_service.py` — LinkedIn Easy Apply automation + LinkedIn DM sending.
  - `email_service.py` — Brevo SMTP email with PDF attachments.
  - `interview_service.py` — manages multi-turn interview sessions (start/send/help/end).
  - `profile_service.py` — completeness scoring via weighted field checks.

**Storage:** `backend/storage/json_store.py` — all reads/writes go through here. Uses **atomic writes** (write to `.tmp`, then `shutil.move`). Never write JSON files directly — always use `json_store.*` functions. Exception: `cv_service.py` also uses the same atomic pattern directly for `meta.json` writes.

**Models:** `backend/models/schemas.py` — single file with all Pydantic v2 schemas: `ProfileMeta`, `TargetCompany`, `HiringPersona`, `ApplicationMeta`, `ApplicationHistory`, `InterviewSession`, etc.

**Prompts:** `backend/prompts/*.txt` — all system prompts are external text files loaded at runtime. Modifying prompt behavior → edit the `.txt` file, not the Python service. Available prompts: `role_suggest`, `persona_build`, `cv_generate`, `cv_score`, `cv_optimize`, `cover_letter_generate`, `cover_letter_score`, `interview_simulate`, `interview_coach`, `interview_score`, `linkedin_dm`, `language_filter`.

**SSE streaming:** `backend/routers/generation.py` uses in-memory `asyncio.Queue` per `company_id` to stream GAN loop progress to the frontend via Server-Sent Events. The frontend connects to `/api/generation/status/{company_id}` via `EventSource`. SSE queues are process-local and lost on server restart.

---

## Frontend Architecture

**Stack:** React + Vite + Tailwind CSS + React Router

**API client:** `frontend/src/api/client.js` — single `apiClient` object with all backend calls. Base URL: `http://localhost:8000/api`. The internal `request()` function is **not** exported; never call it directly from components.

**Routing:**
- `/` → `Dashboard` (profile card + history table)
- `/discover` → `Discovery` (role suggest → Playwright scrape → target selection)
- `/review` → `Review` (GAN generation with SSE progress + CV preview)
- `/apply` → `Apply` (sequential apply queue with execution log)
- `/interview/:companyId` → `Interview` (live chat simulator + coach overlay + scoring)

**Key components:** `CVPreview.jsx` renders the CV JSON for in-browser preview. `CVEditorModal.jsx` provides inline JSON editing of the generated CV before PDF export. `HelpOverlay.jsx` is the interview coach panel.

**State management:** No global store. Each page fetches its own data. `useProfile` hook in `frontend/src/hooks/useProfile.js` manages profile + completeness globally via prop-drilling through `Layout`.

---

## LLM Integration Notes

- **Model:** `meta-llama/llama-3.3-70b-instruct` via OpenRouter (configured in `config.py → OPENROUTER_MODEL`).
- `call_groq` is the only LLM entry point. Always `await` it.
- When `expect_json=True`, the call sets `response_format: {type: "json_object"}` (except for `suggest_roles` purpose) and auto-parses. If parsing fails, `ValueError` is raised.
- Mock fallback activates when `OPENROUTER_API_KEY` is empty — returns hardcoded dicts keyed by `purpose` prefix.
- The `suggest_roles` endpoint normalizes LLM output: if the model returns `{"roles": [...]}` or similar wrapped objects, `discovery.py` unwraps to the list automatically.

---

## Key Constraints

- **Rate limits:** Max 20 applications/day (`MAX_DAILY_APPLICATIONS`), enforced in `apply.py → _enforce_daily_limit()`. Both `_enforce_daily_limit()` and `get_status()` read directly from `settings.MAX_DAILY_APPLICATIONS`.
- **GAN loop:** `max_loops = settings.MAX_GAN_ITERATIONS` (currently `2`), target score ≥ `settings.MIN_CV_SCORE` (currently `7.5`). Both are read from `config.py` — change them there.
- **Apply delay:** 2–8 seconds random delay between applications (`MIN/MAX_APPLY_DELAY_SECONDS`).
- **Storage:** All state is local JSON. Never introduce a database.
- **PDF rendering:** Uses Playwright Chromium (sync API in a thread executor) with inline Jinja2 templates. `render_cv_to_pdf()` in `cv_service.py` handles both CV and cover letter.

---

## Logging

- `logs/decisions.log` — structured AI decision log (purpose, model, tokens, score per iteration).
- `logs/debug.log` — error traces and scraping outcomes.
- `logs/todo.md` / `logs/done.md` — live task tracker. Update these when completing tasks.
