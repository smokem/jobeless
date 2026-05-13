import logging
import os
from typing import List
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.services.interview_service import start_session, send_message, get_help, end_session

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/{company_id}/start")
async def start_interview_endpoint(company_id: str):
    """Initializes new interview iteration"""
    try:
        session = await start_session(company_id)
        return session.model_dump(mode="json")
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{company_id}/{session_id}/message")
async def process_message_endpoint(company_id: str, session_id: str, body: dict):
    """Processes chat iterations natively to Groq"""
    msg = body.get("message")
    if not msg:
        raise HTTPException(status_code=400, detail="Message is required")
        
    try:
        reply = await send_message(company_id, session_id, msg)
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Failed to send session message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{company_id}/{session_id}/help")
async def get_help_endpoint(company_id: str, session_id: str):
    """Triggers side-channel coach response"""
    try:
        coaching = await get_help(company_id, session_id)
        return coaching
    except Exception as e:
        logger.error(f"Help processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{company_id}/{session_id}/end")
async def terminate_session_endpoint(company_id: str, session_id: str):
    """Concludes interview evaluating complete conversation against standard schema filters"""
    try:
        score = await end_session(company_id, session_id)
        return score
    except Exception as e:
        logger.error(f"Session termination / scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{company_id}/sessions")
async def list_sessions(company_id: str):
    """Fetch historic session overviews"""
    dir_path = settings.INTERVIEW_SESSIONS_DIR / company_id
    if not dir_path.exists():
        return []
    
    # Just list to show how many previous encounters occurred
    files = list(dir_path.glob("*.json"))
    return [{"session_id": f.stem} for f in files]

@router.delete("/{company_id}/sessions")
async def clear_sessions(company_id: str):
    """Purge target historical session logs safely"""
    dir_path = settings.INTERVIEW_SESSIONS_DIR / company_id
    if dir_path.exists():
        for f in dir_path.glob("*.json"):
            try:
                f.unlink()
            except:
                pass
    return {"status": "cleared"}
