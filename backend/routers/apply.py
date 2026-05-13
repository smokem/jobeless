import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.storage import json_store
from backend.models.schemas import ApplicationHistory
from backend.services.playwright_service import easy_apply, send_linkedin_dm
from backend.services.email_service import send_application_email

logger = logging.getLogger(__name__)

router = APIRouter()

def _enforce_daily_limit(count_to_add=1):
    history_entries = json_store.read_history()
    today_str = datetime.now().strftime("%Y-%m-%d")
    sent_today = len([e for e in history_entries if e.date_sent.strftime("%Y-%m-%d") == today_str])
    max_limit = getattr(settings, "MAX_APPLICATIONS_PER_DAY", 20)
    
    if sent_today + count_to_add > max_limit:
        raise HTTPException(
            status_code=429, 
            detail=f"Daily limit of {max_limit} applications reached. {sent_today} sent today."
        )

@router.get("/status")
def get_status():
    history_entries = json_store.read_history()
    today_str = datetime.now().strftime("%Y-%m-%d")
    sent_today = len([e for e in history_entries if e.date_sent.strftime("%Y-%m-%d") == today_str])
    max_limit = getattr(settings, "MAX_APPLICATIONS_PER_DAY", 20)
    
    targets = json_store.read_targets()
    pending = [t for t in targets if t.status == "pending"]
    
    return {
        "sent_today": sent_today,
        "max_limit": max_limit,
        "remaining_today": max_limit - sent_today,
        "pending_targets": len(pending),
        "total_targets": len(targets)
    }

@router.post("/run/{company_id}")
async def apply_to_target(company_id: str):
    _enforce_daily_limit(1)
    
    targets = json_store.read_targets()
    target = next((t for t in targets if t.company_id == company_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if target.status != "pending":
        raise HTTPException(status_code=400, detail="Target is not pending")
        
    target_dir = Path(settings.DATA_DIR) / "applications" / company_id
    cv_pdf = target_dir / "cv.pdf"
    cl_pdf = target_dir / "cover_letter.pdf"
    
    if not cv_pdf.exists():
        raise HTTPException(status_code=400, detail="CV PDF not found. Ensure CV generation completed.")
        
    logger.info(f"Applying to {target.company_name} via {target.apply_type}")
    
    result = {"success": False, "error": "Unknown apply type"}
    if target.apply_type == "easy_apply":
        result = await easy_apply(target, str(cv_pdf))
    elif target.apply_type == "email":
        subject = f"Application for {target.job_title} - Zied Cherif"
        body = f"Hello,\n\nPlease find attached my CV and Cover Letter for the {target.job_title} role at {target.company_name}.\n\nBest regards,\nZied Cherif"
        
        result = await send_application_email(target, str(cv_pdf), str(cl_pdf) if cl_pdf.exists() else str(cv_pdf), subject, body)
        
        if result.get("success") and target.hr_linkedin:
            dm_msg = f"Hi, I applied via email for the {target.job_title} role. Enthusiastic to connect!"
            await send_linkedin_dm(str(target.hr_linkedin), dm_msg)
            
    history_entries = json_store.read_history()
    
    # Store outcome
    new_entry = ApplicationHistory(
        company_id=target.company_id,
        company_name=target.company_name,
        job_title=target.job_title,
        date_sent=datetime.now(),
        apply_method=target.apply_type,
        cv_score_achieved=9.0, # Target pass score
        status="sent" if result.get("success") else "rejected", # 'rejected' represents failed to send here for simplicity in UI mapping
        cv_path=str(cv_pdf),
        cl_path=str(cl_pdf) if cl_pdf.exists() else "",
        notes=result.get("error")
    )
    
    history_entries.append(new_entry)
    json_store.write_history(history_entries)
    
    target.status = "ignored" if not result.get("success") else "applied"
    
    for i, t in enumerate(targets):
        if t.company_id == company_id:
            targets[i] = target
    json_store.write_targets(targets)
    
    # Log decision
    log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DECISION] module=apply_router function=apply_to_target company={target.company_name} success={result.get('success')} method={target.apply_type}\n"
    log_path = Path(settings.DEBUG_LOG).parent / "decisions.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Could not log decision: {e}")
        
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to apply"))
        
    return result
