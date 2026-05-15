# AI Moves Log

## 2026-05-14 — Fix Interview Simulator Schema Mismatch
**Prompt**: bug with 500 error when starting interview and validation info missing, loading.json errors, and react router warnings.
**Approach**: I migrated the `target_info` key to `company_info` in `meta.json` using a Python script, fixed `cv_service.py` to write `company_info` onwards, and silenced the React Router warnings. Currently examining `loading.json` bug in `frontend/src/pages/Interview.jsx`.
**Files touched**: backend/services/cv_service.py, frontend/src/App.jsx
**Outcome**: PARTIAL
**Notes**: Need to fix the `loading.json` frontend bug and vite.svg not found.
