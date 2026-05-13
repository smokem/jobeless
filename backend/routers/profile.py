"""
Profile router — handles profile CRUD and completeness scoring.

Endpoints:
  GET  /           → Read and return full profile
  PATCH /          → Partial update, merge with existing, atomic write
  GET  /completeness → Return completeness score and missing fields
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from backend.storage import json_store
from backend.services.profile_service import calculate_completeness

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_profile():
    """
    Read and return data/profile.json validated against ProfileMeta schema.

    Returns:
        dict: The validated profile data.

    Raises:
        HTTPException 404: If profile.json doesn't exist.
        HTTPException 422: If profile.json fails schema validation.
        HTTPException 500: On unexpected read errors.
    """
    try:
        profile = json_store.read_profile()
        return profile.model_dump(mode="json")
    except FileNotFoundError as e:
        logger.error(f"Profile file not found: {e}")
        raise HTTPException(status_code=404, detail="Profile file not found.")
    except ValidationError as e:
        logger.error(f"Profile validation failed: {e}")
        raise HTTPException(status_code=422, detail=f"Profile validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to read profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read profile: {str(e)}")


@router.patch("/")
async def patch_profile(updates: dict):
    """
    Accept partial update, deep-merge with existing profile, atomic write, return updated.

    Args:
        updates: A dict of fields to update (can be nested).

    Returns:
        dict: The merged and validated profile data.

    Raises:
        HTTPException 404: If profile.json doesn't exist.
        HTTPException 422: If merged result fails schema validation.
        HTTPException 500: On unexpected write errors.
    """
    try:
        existing = json_store.read_raw_profile()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Profile file not found.")
    except Exception as e:
        logger.error(f"Failed to read profile for patching: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read profile: {str(e)}")

    # Deep merge
    merged = _deep_merge(existing, updates)

    try:
        # Validate merged profile against schema before writing
        from backend.models.schemas import ProfileMeta
        validated = ProfileMeta.model_validate(merged)
    except ValidationError as e:
        logger.error(f"Merged profile fails validation: {e}")
        raise HTTPException(status_code=422, detail=f"Update would create invalid profile: {str(e)}")

    try:
        json_store.write_profile(merged)
    except Exception as e:
        logger.error(f"Failed to write profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {str(e)}")

    return validated.model_dump(mode="json")


@router.get("/completeness")
async def get_completeness():
    """
    Return completeness score and list of missing fields.

    Returns:
        dict: {score: float, missing_fields: list[str]}

    Raises:
        HTTPException 404: If profile.json doesn't exist.
        HTTPException 500: On unexpected errors.
    """
    try:
        raw_profile = json_store.read_raw_profile()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Profile file not found.")
    except Exception as e:
        logger.error(f"Failed to read profile for completeness: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    result = calculate_completeness(raw_profile)
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override into base. Override values win for non-dict fields.

    Args:
        base: The existing dictionary.
        override: The dictionary with updates to apply.

    Returns:
        dict: A new merged dictionary.
    """
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
