import logging
import json
import re
import time
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from backend.storage import json_store
from backend.services.groq_service import call_groq
from backend.services.apify_service import scrape_linkedin_jobs
from backend.models.schemas import TargetCompany
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _flatten_skills(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return [s.get("name", "") if isinstance(s, dict) else str(s) for s in raw if s][:10]
    if isinstance(raw, dict):
        result = []
        for items in raw.values():
            if isinstance(items, list):
                for item in items:
                    result.append(item.get("name", "") if isinstance(item, dict) else str(item))
        return [s for s in result if s][:10]
    return []


class ScrapeRequest(BaseModel):
    role: str = Field(..., description="The job title or keywords to search for.")
    location: str = Field(..., description="City, country, or 'remote'.")
    radius_km: int = Field(25, description="Search radius around location.")


class FinalizeTargetsRequest(BaseModel):
    ids: list[str] = Field(..., description="List of company_ids to keep.")


class ManualTargetRequest(BaseModel):
    company_name: str = Field(..., description="Company name.")
    job_title: str = Field(..., description="Role you are applying for.")
    job_url: str = Field(..., description="Direct URL to the job posting.")
    location: str = Field(..., description="Job location or 'Remote'.")
    apply_type: Literal["easy_apply", "email", "external"] = Field("external")
    company_linkedin: Optional[str] = Field(None)
    company_website: Optional[str] = Field(None)
    hr_name: Optional[str] = Field(None)
    hr_linkedin: Optional[str] = Field(None)
    ceo_name: Optional[str] = Field(None)
    ceo_linkedin: Optional[str] = Field(None)


def _ensure_https(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


@router.get("/suggest-roles")
async def suggest_roles():
    try:
        profile_data = json_store.read_raw_profile()
        pi = profile_data.get("personal_info", {})
        slim = {
            "headline":   pi.get("headline"),
            "summary":    (pi.get("summary") or "")[:200],
            "skills":     _flatten_skills(profile_data.get("skills") or profile_data.get("technical_skills")),
            "experience": [
                {"role": e.get("role") or e.get("title"), "company": e.get("company")}
                for e in (profile_data.get("experience") or [])[:4]
            ],
            "education":  [
                {"degree": e.get("degree"), "field": e.get("field")}
                for e in (profile_data.get("education") or [])[:2]
            ],
        }
        profile_json = json.dumps(slim)
    except Exception as e:
        logger.error(f"Failed to read profile for role suggestion: {e}")
        raise HTTPException(status_code=500, detail="Could not read profile data.")

    try:
        prompt_path = settings.BASE_DIR / "backend" / "prompts" / "role_suggest.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except Exception as e:
        logger.error(f"Failed to load role_suggest.txt: {e}")
        raise HTTPException(status_code=500, detail="Missing prompt configuration.")

    user_message = f"Please analyze my profile and suggest roles:\n\n{profile_json}"

    try:
        suggestions = await call_groq(
            system_prompt=system_prompt,
            user_message=user_message,
            expect_json=True,
            purpose="suggest_roles"
        )
        if isinstance(suggestions, list):
            return suggestions
        if isinstance(suggestions, dict):
            for key in ("value", "roles", "suggestions", "data", "results", "items"):
                if key in suggestions and isinstance(suggestions[key], list):
                    return suggestions[key]
            for v in suggestions.values():
                if isinstance(v, list):
                    return v
        return suggestions
    except ValueError as e:
        logger.error(f"Groq returned malformed JSON: {e}")
        raise HTTPException(status_code=502, detail="AI returned malformed response.")
    except Exception as e:
        logger.error(f"Groq call failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to communicate with AI.")


async def _filter_targets_by_language(targets: list[TargetCompany], langs: list[str]) -> list[TargetCompany]:
    if not langs or not targets:
        return targets
        
    prompt_path = settings.BASE_DIR / "backend" / "prompts" / "language_filter.txt"
    if not prompt_path.exists():
        return targets
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read().format(languages=", ".join(langs))
        
    targets_data = [{"company_id": t.company_id, "location": t.location, "title": t.job_title} for t in targets]
    user_message = json.dumps(targets_data)
    
    try:
        response = await call_groq(
            system_prompt=system_prompt,
            user_message=user_message,
            expect_json=True,
            purpose="filter_languages"
        )
        kept_ids = set(response.get("kept_company_ids", []))
        if not kept_ids:
            return targets
        filtered = [t for t in targets if t.company_id in kept_ids]
        return filtered if filtered else targets
    except Exception as e:
        logger.error(f"Error checking languages with LLM: {e}")
        return targets


@router.post("/scrape")
async def scrape_jobs(params: ScrapeRequest):
    try:
        targets = await scrape_linkedin_jobs(
            role=params.role,
            location=params.location,
            radius_km=params.radius_km
        )
        
        try:
            profile_data = json_store.read_raw_profile()
            langs = [
                l.get("language") for l in profile_data.get("personal_info", {}).get("languages", [])
                if l.get("language")
            ]
            if langs:
                targets = await _filter_targets_by_language(targets, langs)
        except Exception as filter_err:
            logger.warning(f"Failed to filter targets by language: {filter_err}")
            
        json_store.write_targets(targets)
        return {
            "count": len(targets),
            "preview": [t.model_dump(mode="json") for t in targets]
        }
    except Exception as e:
        logger.error(f"Failed to scrape jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/targets")
async def get_targets():
    try:
        targets = json_store.read_targets()
        return [t.model_dump(mode="json") for t in targets]
    except Exception as e:
        logger.error(f"Failed to read targets: {e}")
        raise HTTPException(status_code=500, detail="Could not read targets.")


@router.post("/targets/finalize")
async def finalize_targets(req: FinalizeTargetsRequest):
    try:
        targets = json_store.read_targets()
        selected_ids = set(req.ids)
        for t in targets:
            t.status = "pending" if t.company_id in selected_ids else "ignored"
        json_store.write_targets(targets)
        return {"status": "success", "count": len(targets)}
    except Exception as e:
        logger.error(f"Failed to finalize targets: {e}")
        raise HTTPException(status_code=500, detail="Could not finalize targets.")


@router.post("/targets/manual")
async def add_manual_target(req: ManualTargetRequest):
    """Add a job listing manually without scraping."""
    try:
        slug = re.sub(r"[^a-z0-9]+", "-", req.company_name.lower()).strip("-")[:24]
        company_id = f"manual_{int(time.time())}_{slug}"

        linkedin_url = _ensure_https(req.company_linkedin)
        if not linkedin_url:
            linkedin_url = f"https://www.linkedin.com/company/{slug}"

        target = TargetCompany(
            company_id=company_id,
            company_name=req.company_name,
            company_linkedin=linkedin_url,
            company_website=_ensure_https(req.company_website),
            hr_name=req.hr_name or None,
            hr_linkedin=_ensure_https(req.hr_linkedin),
            ceo_name=req.ceo_name or None,
            ceo_linkedin=_ensure_https(req.ceo_linkedin),
            job_title=req.job_title,
            job_url=_ensure_https(req.job_url) or req.job_url,
            apply_type=req.apply_type,
            location=req.location,
            status="pending"
        )

        existing = json_store.read_targets()
        existing.append(target)
        json_store.write_targets(existing)

        return target.model_dump(mode="json")
    except Exception as e:
        logger.error(f"Failed to add manual target: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/targets/{company_id}")
async def delete_target(company_id: str):
    """Remove a target from the list."""
    try:
        targets = json_store.read_targets()
        updated = [t for t in targets if t.company_id != company_id]
        if len(updated) == len(targets):
            raise HTTPException(status_code=404, detail="Target not found.")
        json_store.write_targets(updated)
        return {"status": "deleted", "company_id": company_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete target: {e}")
        raise HTTPException(status_code=500, detail=str(e))
