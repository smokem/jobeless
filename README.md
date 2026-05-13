# AutoApply Platform - Jobless.io

An autonomous, AI-powered platform for navigating the complete job search lifecycle. From intelligent role discovery and GAN-engineered resumes to headless Playwright applications and persona-driven interview simulations.

## Prerequisites
- Python 3.11+
- Node.js 18+
- Playwright (Chromium)
- Apify account (for LinkedIn scraping)
- Groq account (for fast LLM inference)
- Brevo account (for SMTP application routing)

## Setup

1. **Clone this repository** to your local machine.
2. **Environment Variables**: Copy `.env.example` to a new `.env` file and populate your respective API keys (`GROQ_API_KEY`, `APIFY_TOKEN`, `BREVO_SMTP_PASSWORD`, `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`).
3. **Backend Initialization**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   playwright install chromium
   ```
4. **Frontend Initialization**:
   ```bash
   cd frontend
   npm install
   ```
5. **Data Hydration**: Ensure your base profile details are recorded properly at `data/profile.json`.

## Run

You will need to run the backend API schema and the frontend UI concurrently.

**Terminal 1 (Backend - FastAPI)**
```bash
uvicorn backend.main:app --reload
```

**Terminal 2 (Frontend - React/Vite)**
```bash
cd frontend
npm run dev
```

## Usage Lifecycle

1. **Dashboard (Phase 1/6)**: Review your completeness score and historical application timelines.
2. **Discovery (Phase 2)**: Let Groq interpret your profile to recommend target job roles, subsequently invoking Apify to scrape real LinkedIn listings.
3. **Review (Phases 3/4)**: Initialize research sub-agents calculating specific HR hiring personas. Run the Generator/Discriminator LLM loops crafting highly optimized PDFs targeted explicitly to these personas.
4. **Apply Queue (Phase 5)**: Track automated outreach utilizing Playwright and Brevo acting on pre-rendered artifacts mitigating rate limitations.
5. **Interview Simulator (Phase 7)**: Interactive local prompt sessions mimicking identified HR patterns dynamically scoring transcriptions.

## File Structure Overview
Refer carefully to `PRD.md` located in the root of the structure for an intense mapping of standard file deployments and core routing mechanics. Every micro-service maintains distinct skill files under `/skills` outlining deterministic workflow architectures.
