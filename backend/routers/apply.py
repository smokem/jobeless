import asyncio
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

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
    max_limit = settings.MAX_DAILY_APPLICATIONS
    if sent_today + count_to_add > max_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit of {max_limit} applications reached. {sent_today} sent today."
        )


def _get_candidate_name() -> str:
    try:
        profile = json_store.read_profile()
        return (profile.personal_info.full_name or "").strip() or "The Applicant"
    except Exception:
        return "The Applicant"


async def _apply_single(target, cv_pdf: Path, cl_pdf: Path) -> dict:
    """Core apply logic for a single target. Returns result dict."""
    if target.apply_type == "easy_apply":
        return await easy_apply(target, str(cv_pdf))

    if target.apply_type == "email":
        candidate_name = _get_candidate_name()
        subject = f"Application for {target.job_title} – {candidate_name}"
        body = (
            f"Hello,\n\n"
            f"Please find attached my CV and Cover Letter for the {target.job_title} role "
            f"at {target.company_name}.\n\n"
            f"Best regards,\n{candidate_name}"
        )
        result = await send_application_email(
            target, str(cv_pdf), str(cl_pdf) if cl_pdf.exists() else str(cv_pdf), subject, body
        )
        if result.get("success") and target.hr_linkedin:
            dm_msg = f"Hi, I applied via email for the {target.job_title} role. Enthusiastic to connect!"
            await send_linkedin_dm(str(target.hr_linkedin), dm_msg)
        return result

    return {"success": False, "error": "Unknown apply type"}


def _record_result(target, cv_pdf: Path, cl_pdf: Path, result: dict) -> None:
    """Write outcome to history.json and flip target status."""
    target_dir = Path(settings.DATA_DIR) / "applications" / target.company_id
    cv_score = settings.MIN_CV_SCORE
    iter_path = target_dir / "cv_iterations.json"
    try:
        if iter_path.exists():
            with open(iter_path, "r", encoding="utf-8") as f:
                iters = json.load(f)
            if iters:
                cv_score = iters[-1].get("score", settings.MIN_CV_SCORE)
    except Exception:
        pass

    history_entries = json_store.read_history()
    history_entries.append(ApplicationHistory(
        company_id=target.company_id,
        company_name=target.company_name,
        job_title=target.job_title,
        date_sent=datetime.now(),
        apply_method=target.apply_type,
        cv_score_achieved=cv_score,
        status="sent" if result.get("success") else "rejected",
        cv_path=str(cv_pdf),
        cl_path=str(cl_pdf) if cl_pdf.exists() else "",
        notes=result.get("error"),
    ))
    json_store.write_history(history_entries)

    targets = json_store.read_targets()
    for i, t in enumerate(targets):
        if t.company_id == target.company_id:
            targets[i].status = "applied" if result.get("success") else "ignored"
    json_store.write_targets(targets)

    log_entry = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [DECISION] "
        f"module=apply_router company={target.company_name} "
        f"success={result.get('success')} method={target.apply_type}\n"
    )
    log_path = Path(settings.DEBUG_LOG).parent / "decisions.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Could not log decision: {e}")


# ── Status ──────────────────────────────────────────────────────────────────

@router.get("/status")
def get_status():
    history_entries = json_store.read_history()
    today_str = datetime.now().strftime("%Y-%m-%d")
    sent_today = len([e for e in history_entries if e.date_sent.strftime("%Y-%m-%d") == today_str])
    max_limit = settings.MAX_DAILY_APPLICATIONS
    targets = json_store.read_targets()
    pending = [t for t in targets if t.status == "pending"]
    return {
        "sent_today": sent_today,
        "max_limit": max_limit,
        "remaining_today": max_limit - sent_today,
        "pending_targets": len(pending),
        "total_targets": len(targets),
    }


# ── Single-target endpoint (kept for direct use) ────────────────────────────

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
    if target.apply_type == "external":
        raise HTTPException(status_code=400, detail=f"External jobs must be applied manually: {target.job_url}")

    result = await _apply_single(target, cv_pdf, cl_pdf)
    _record_result(target, cv_pdf, cl_pdf, result)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to apply"))
    return result


# ── Batch SSE endpoint ───────────────────────────────────────────────────────

@router.get("/batch/stream")
async def batch_apply_stream(request: Request):
    """
    SSE stream that runs all pending auto-apply targets sequentially.
    Each message is one of:
      PREPARING|company_id|company_name
      DONE_ONE|company_id|company_name|success|failed
      ERROR_ONE|company_id|company_name|<error text>
      WAITING|<seconds>
      TICK|<seconds_left>
      LIMIT_REACHED|<max>
      BATCH_DONE
    """

    async def event_generator():
        try:
            all_targets = json_store.read_targets()
            auto_targets = [
                t for t in all_targets
                if t.status == "pending" and t.apply_type != "external"
            ]

            if not auto_targets:
                yield "data: BATCH_DONE\n\n"
                return

            history_entries = json_store.read_history()
            today_str = datetime.now().strftime("%Y-%m-%d")
            sent_today = len([
                e for e in history_entries
                if e.date_sent.strftime("%Y-%m-%d") == today_str
            ])

            for idx, target in enumerate(auto_targets):
                if await request.is_disconnected():
                    return

                if sent_today >= settings.MAX_DAILY_APPLICATIONS:
                    yield f"data: LIMIT_REACHED|{settings.MAX_DAILY_APPLICATIONS}\n\n"
                    return

                target_dir = Path(settings.DATA_DIR) / "applications" / target.company_id
                cv_pdf = target_dir / "cv.pdf"
                cl_pdf = target_dir / "cover_letter.pdf"

                if not cv_pdf.exists():
                    yield f"data: ERROR_ONE|{target.company_id}|{target.company_name}|CV not generated yet\n\n"
                    continue

                yield f"data: PREPARING|{target.company_id}|{target.company_name}\n\n"

                try:
                    result = await _apply_single(target, cv_pdf, cl_pdf)
                    _record_result(target, cv_pdf, cl_pdf, result)
                    outcome = "success" if result.get("success") else "failed"
                    yield f"data: DONE_ONE|{target.company_id}|{target.company_name}|{outcome}\n\n"
                    if result.get("success"):
                        sent_today += 1
                except Exception as e:
                    logger.error(f"Batch apply failed for {target.company_name}: {e}", exc_info=True)
                    yield f"data: ERROR_ONE|{target.company_id}|{target.company_name}|{str(e)}\n\n"

                # Inter-application delay — sleep in 1-second ticks so the UI can show a countdown
                if idx < len(auto_targets) - 1:
                    delay = random.randint(
                        settings.MIN_APPLY_DELAY_SECONDS,
                        settings.MAX_APPLY_DELAY_SECONDS,
                    )
                    yield f"data: WAITING|{delay}\n\n"
                    for remaining in range(delay, 0, -1):
                        if await request.is_disconnected():
                            return
                        yield f"data: TICK|{remaining}\n\n"
                        await asyncio.sleep(1)

            yield "data: BATCH_DONE\n\n"

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
