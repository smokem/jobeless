from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from backend.storage import json_store

logger = logging.getLogger(__name__)
router = APIRouter()

class StatusUpdate(BaseModel):
    status: str

@router.get("/")
async def get_history():
    """Returns the application history from history.json."""
    try:
        history = json_store.read_history()
        return [h.model_dump(mode="json") for h in history]
    except Exception as e:
        logger.error(f"Failed to read history: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not read history.")

@router.patch("/{company_id}/status")
async def update_history_status(company_id: str, req: StatusUpdate):
    """Updates the status of a specific history item."""
    try:
        history = json_store.read_history()
        updated = False
        for item in history:
            if item.company_id == company_id:
                item.status = req.status
                updated = True
                break
        if updated:
            json_store.write_history(history)
            return {"status": "success", "company_id": company_id, "new_status": req.status}
        else:
            raise HTTPException(status_code=404, detail="Company ID not found in history.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update history status: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not update history status.")
