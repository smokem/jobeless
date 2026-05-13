# 📋 AutoApply Platform — Product Requirements Document (PRD)

> **Version:** 1.0 | **Owner:** Zied Cherif | **Status:** Pre-Development  
> **Last Updated:** 2026-05-04  
> **Storage:** 100% local JSON — no database, no XAMPP, no PHP, no SQL

---

## 1. Executive Summary

AutoApply is a local AI-powered job application automation platform. It analyzes the user's professional profile, discovers relevant job listings, generates hyper-tailored CVs and cover letters per company (using a GAN-style scoring loop), auto-applies via email and LinkedIn Easy Apply, and simulates interviews using a persona built from the target company's HR/CEO public data.

**The user touches nothing between "start" and "interview scheduled."**

---

## 2. Goals & Non-Goals

### Goals
- Automate 100% of the job application pipeline from discovery to send
- Generate a unique, scored CV + cover letter per company (never reuse)
- Simulate the real interviewer to let the user practice before showing up
- Store all state locally as JSON — portable, offline-capable, no server needed
- Run entirely on free-tier tools (Groq, Apify free, Playwright, Brevo)

### Non-Goals
- Not a general-purpose job board
- Not a resume builder for manual editing
- No cloud database, no SQL, no XAMPP
- No paid API tiers required to run core features

---

## 3. User Personas

**Primary User: Zied Cherif**
- Full-stack developer with AI/ML background
- Located in Sfax, Tunisia; open to remote & relocation
- Fluent in Arabic, French, English (B2)
- Targeting: Frontend, Flutter, Full-Stack, AI/ML, Creative Tech roles
- Profile source: `data/profile.json`

---

## 4. System Architecture Overview

```
autoapply/
├── data/
│   ├── profile.json          ← Source of truth (Zied's full profile)
│   ├── targets.json          ← Scraped job listings per session
│   ├── applications/
│   │   └── {company_id}/
│   │       ├── meta.json     ← Company info, HR persona, scores
│   │       ├── cv.json       ← Generated CV data
│   │       ├── cv.pdf        ← Rendered CV (1 page)
│   │       ├── cover_letter.json
│   │       └── cover_letter.pdf
│   ├── history.json          ← All application statuses
│   └── interview_sessions/
│       └── {company_id}/
│           └── {session_id}.json
├── skills/
│   ├── cv-generation.md
│   ├── company-research.md
│   ├── gan-scoring.md
│   ├── playwright-automation.md
│   ├── email-sending.md
│   └── interview-simulation.md
├── logs/
│   ├── decisions.log         ← AI reasoning logs
│   ├── debug.log             ← Error traces and fixes
│   ├── todo.md               ← Live task tracker
│   └── done.md               ← Completed tasks + how they were done
├── umls/
│   ├── phase1_profile.puml
│   ├── phase2_discovery.puml
│   ├── phase3_apply.puml
│   ├── phase4_tracking.puml
│   └── phase5_interview.puml
├── frontend/                 ← React + Tailwind
├── backend/                  ← FastAPI (Python)
├── .antigravity              ← Agent rules (see RULES.md)
├── PRD.md                    ← This file
└── RULES.md                  ← Antigravity agent rules
```

---

## 5. Phases & Feature Requirements

---

### Phase 1 — Profile Foundation
**Status:** ✅ Done (profile.json exists)

| ID | Requirement | Priority |
|----|-------------|----------|
| P1-01 | Load `data/profile.json` on app start | MUST |
| P1-02 | Display completeness score and missing fields | MUST |
| P1-03 | Allow manual field completion via UI form | SHOULD |
| P1-04 | Validate JSON schema on load, surface errors | MUST |

**Data Contract:** `profile.json` schema defined. Fields: `personal_info`, `education`, `work_experience`, `skills`, `projects`, `certifications`, `personality_and_work_style`, `preferences_and_goals`, `cv_generation_hints`.

---

### Phase 2 — Job Discovery

| ID | Requirement | Priority |
|----|-------------|----------|
| P2-01 | Groq suggests 5–10 job roles based on `profile.json` | MUST |
| P2-02 | User selects a role from dropdown | MUST |
| P2-03 | User enters location (city, country, or "remote") | MUST |
| P2-04 | User sets search radius (km) | MUST |
| P2-05 | Apify scrapes LinkedIn for matching jobs | MUST |
| P2-06 | Display count of discovered companies | MUST |
| P2-07 | Save results to `data/targets.json` | MUST |
| P2-08 | User reviews and de-selects unwanted targets | SHOULD |

**Apify Actor:** `apify/linkedin-jobs-scraper` (or equivalent maintained actor)  
**Output schema per target:**
```json
{
  "company_id": "uuid",
  "company_name": "string",
  "company_linkedin": "url",
  "company_website": "url",
  "hr_name": "string|null",
  "hr_linkedin": "url|null",
  "ceo_name": "string|null",
  "ceo_linkedin": "url|null",
  "job_title": "string",
  "job_url": "string",
  "apply_type": "easy_apply|email|external",
  "location": "string",
  "status": "pending"
}
```

---

### Phase 3 — Company Research

| ID | Requirement | Priority |
|----|-------------|----------|
| P3-01 | For each target: scrape company LinkedIn page | MUST |
| P3-02 | Scrape CEO LinkedIn posts (last 20 posts) | MUST |
| P3-03 | Scrape HR LinkedIn posts (last 20 posts) | MUST |
| P3-04 | Scrape company Twitter/X if URL found | SHOULD |
| P3-05 | Groq synthesizes a "hiring persona" from scraped data | MUST |
| P3-06 | Persona stored in `applications/{company_id}/meta.json` | MUST |

**Persona schema:**
```json
{
  "company_values": ["string"],
  "hr_communication_style": "string",
  "what_they_look_for": ["string"],
  "red_flags_to_avoid": ["string"],
  "cultural_keywords": ["string"],
  "tone_preference": "formal|casual|technical"
}
```

---

### Phase 4 — GAN-Style CV Generation Loop

| ID | Requirement | Priority |
|----|-------------|----------|
| P4-01 | Groq Instance B generates CV JSON from `profile.json` + persona | MUST |
| P4-02 | Groq Instance A (HR persona) scores the CV (0–10) with notes | MUST |
| P4-03 | If score < 9: feed notes back to Instance B and regenerate | MUST |
| P4-04 | Max 5 iterations per CV (prevent infinite loops) | MUST |
| P4-05 | Log each iteration: score, notes, changes made | MUST |
| P4-06 | Render final CV JSON to 1-page PDF | MUST |
| P4-07 | Same loop for cover letter (separate GAN loop) | MUST |
| P4-08 | CV structure: Education (top) → Experience → Projects → Skills → Soft Skills (bottom) | MUST |

---

### Phase 5 — Auto Apply

| ID | Requirement | Priority |
|----|-------------|----------|
| P5-01 | For `apply_type: easy_apply`: use Playwright to automate LinkedIn Easy Apply | MUST |
| P5-02 | For `apply_type: email`: send email via Brevo SMTP with CV + CL as PDF attachment | MUST |
| P5-03 | For `apply_type: email`: also send a LinkedIn DM to HR via Playwright | SHOULD |
| P5-04 | Rate limit: max 20 applications/day, 3-second delay between actions | MUST |
| P5-05 | Human-like behavior: random delays (2–8s), scrolling before clicking | MUST |
| P5-06 | On success: update `history.json` with status = "sent" + timestamp | MUST |
| P5-07 | On failure: log error, mark status = "failed", continue queue | MUST |
| P5-08 | All sent CVs and CLs saved locally in `applications/{company_id}/` | MUST |

---

### Phase 6 — Tracking Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| P6-01 | Display all applications from `history.json` in a table | MUST |
| P6-02 | Columns: Company, Role, Date Sent, Status, Score Achieved, Actions | MUST |
| P6-03 | Status values: `pending` / `sent` / `opened` / `replied` / `interview` / `rejected` | MUST |
| P6-04 | Manual status update (user marks "got interview") | MUST |
| P6-05 | Filter by status, date, role | SHOULD |
| P6-06 | Click company → view CV + CL that was sent | MUST |

---

### Phase 7 — Interview Simulator

| ID | Requirement | Priority |
|----|-------------|----------|
| P7-01 | User selects a company from history with status = "interview" | MUST |
| P7-02 | Load company persona from `meta.json` | MUST |
| P7-03 | Groq role-plays as CEO/HR persona in a live chat | MUST |
| P7-04 | "Help Me" button pauses interview, shows: coaching tip for current question, ideal answer structure, subtext/intent behind the question | MUST |
| P7-05 | End session → Groq scores the user's performance (0–10) with detailed breakdown | MUST |
| P7-06 | Save session to `interview_sessions/{company_id}/{session_id}.json` | MUST |
| P7-07 | User can retry (new session) or reset (clear all sessions for that company) | MUST |

---

## 6. Tech Stack

| Layer | Tool | Version | Cost |
|-------|------|---------|------|
| Frontend | React + Tailwind CSS | Latest | Free |
| Backend | FastAPI | Python 3.11+ | Free |
| LLM | Groq API (Llama 3.3 70b) | Latest | Free tier |
| Job Scraping | Apify LinkedIn Jobs Actor | Latest | Free tier |
| Social Scraping | Apify LinkedIn Profile Actor | Latest | Free tier |
| Browser Automation | Playwright (Python) | Latest | Free |
| Email | Brevo (ex-Sendinblue) SMTP | Free tier 300/day | Free |
| PDF Generation | WeasyPrint or ReportLab | Latest | Free |
| Storage | Local JSON files | — | Free |
| Logging | Python logging → `.log` files | — | Free |

---

## 7. Data Flow Diagram (Textual)

```
profile.json
     │
     ▼
[Phase 2] Groq → role suggestions → user picks → Apify scrape
     │
     ▼
targets.json
     │
     ▼
[Phase 3] Apify → company/HR/CEO social data → Groq → persona
     │
     ▼
applications/{id}/meta.json
     │
     ▼
[Phase 4] Groq B (generate) ⟷ Groq A (score as HR) → loop until ≥9
     │
     ▼
cv.pdf + cover_letter.pdf
     │
     ▼
[Phase 5] Playwright Easy Apply OR Brevo email + LinkedIn DM
     │
     ▼
history.json (status: sent)
     │
     ▼
[Phase 6] Dashboard → user marks "interview"
     │
     ▼
[Phase 7] Interview Simulator (Groq as HR) → score → retry
```

---

## 8. API Rate Limits & Constraints

- **Groq free tier:** 14,400 tokens/min, 30 req/min → max ~6 GAN loops/min
- **Apify free tier:** $5 credit/month → ~500 actor runs
- **Brevo free:** 300 emails/day → hard limit on daily applications
- **LinkedIn:** no official API → Playwright automation risk → rate limit to 20/day

---

## 9. File Storage Schema

### `data/history.json`
```json
[
  {
    "company_id": "uuid",
    "company_name": "string",
    "job_title": "string",
    "date_sent": "ISO8601",
    "apply_method": "easy_apply|email",
    "cv_score_achieved": 9.2,
    "status": "sent|opened|replied|interview|rejected",
    "cv_path": "applications/uuid/cv.pdf",
    "cl_path": "applications/uuid/cover_letter.pdf",
    "notes": "string"
  }
]
```

---

## 10. Out of Scope (v1)

- Mobile app
- Multi-user support
- Cloud sync
- Job platform integrations beyond LinkedIn (Indeed, Glassdoor — v2)
- Automated follow-up emails (v2)
- Chrome extension (v2)

---

## 11. Success Metrics

| Metric | Target |
|--------|--------|
| CV GAN score achieved | ≥ 9.0 on first 3 iterations |
| Applications sent per session | 10–20 |
| Application-to-interview rate | > 5% |
| Interview simulator sessions per company | ≥ 3 before real interview |
| System uptime (local) | 99% |