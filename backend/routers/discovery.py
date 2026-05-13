import logging
import json
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from backend.storage import json_store
from backend.services.groq_service import call_groq
from backend.services.apify_service import scrape_linkedin_jobs
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

class ScrapeRequest(BaseModel):
    role: str = Field(..., description="The job title or keywords to search for.")
    location: str = Field(..., description="City, country, or 'remote'.")
    radius_km: int = Field(25, description="Search radius around location.")

class FinalizeTargetsRequest(BaseModel):
    ids: list[str] = Field(..., description="List of company_ids to keep.")


@router.get("/suggest-roles")
async def suggest_roles():
    """
    Reads profile, loads prompt, calls Groq to suggest 8 job roles, 
    and returns the JSON array.
    """
    try:
        profile_data = json_store.read_raw_profile()
        profile_json = json.dumps(profile_data, indent=2)
    except Exception as e:
        logger.error(f"Failed to read profile for role suggestion: {e}")
        raise HTTPException(status_code=500, detail="Could not read profile data.")

    try:
        prompt_path = settings.BASE_DIR / "backend" / "prompts" / "role_suggest.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except Exception as e:
        logger.error(f"Failed to load role_suggest.txt prompt: {e}")
        raise HTTPException(status_code=500, detail="Missing Prompt Configuration.")
        
    user_message = f"Please analyze my profile and suggest roles:\n\n{profile_json}"

    try:
        suggestions = call_groq(
            system_prompt=system_prompt,
            user_message=user_message,
            expect_json=True,
            purpose="suggest_roles"
        )
        return suggestions
    except ValueError as e:
        logger.error(f"Groq did not return valid JSON: {str(e)}")
        raise HTTPException(status_code=502, detail="AI returned malformed response.")
    except Exception as e:
        logger.error(f"Groq call failed: {str(e)}")
        raise HTTPException(status_code=502, detail="Failed to communicate with Groq AI.")


@router.post("/scrape")
async def scrape_jobs(params: ScrapeRequest):
    """
    Calls Apify to scrape jobs matching the criteria, writes targets, 
    and returns a count and preview.
    """
    try:
        targets = await scrape_linkedin_jobs(
            role=params.role,
            location=params.location,
            radius_km=params.radius_km
        )
        
        # Merge with existing targets (or just overwrite? PRD says "save results to data/targets.json per session")
        # For a new session, overwriting is appropriate per PRD "session results".
        json_store.write_targets(targets)
        
        return {
            "count": len(targets),
            "preview": [t.model_dump(mode="json") for t in targets]
        }
    except Exception as e:
        logger.error(f"Failed to scrape jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/targets")
async def get_targets():
    """Returns the current list of target companies from targets.json."""
    try:
        targets = json_store.read_targets()
        return [t.model_dump(mode="json") for t in targets]
    except Exception as e:
        logger.error(f"Failed to read targets: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not read targets.")


@router.post("/targets/finalize")
async def finalize_targets(req: FinalizeTargetsRequest):
    """
    Updates the target.json to mark unselected targets as 'ignored',
    keeping only the selected ones as 'pending'.
    """
    try:
        targets = json_store.read_targets()
        selected_ids = set(req.ids)
        
        updated_targets = []
        for t in targets:
            if t.company_id in selected_ids:
                t.status = "pending"
            else:
                t.status = "ignored"
            updated_targets.append(t)
            
        json_store.write_targets(updated_targets)
        return {"status": "success", "count": len(updated_targets)}
    except Exception as e:
        logger.error(f"Failed to finalize targets: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not finalize targets.")
