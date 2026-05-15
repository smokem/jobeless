# Bugs

## BUG-1 — Interview Validation Error
**Symptom**: 500 Error when starting interview due to 1 validation error for ApplicationMeta: company_info field required.
**File/line**: backend/routers/interview.py, backend/services/cv_service.py
**Root cause**: cv_service.py writes `target_info` to `meta.json` instead of `company_info` which schema `ApplicationMeta` expects.
**Attempts**:
[2026-05-14] Attempt 1: Run Python script to migrate `target_info` to `company_info` in existing `meta.json` files and updated `cv_service.py` to write `company_info`. -> SUCCESS
**Status**: RESOLVED
