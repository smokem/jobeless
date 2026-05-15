import asyncio
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse

from backend.storage import json_store
from backend.services.cv_service import research_company, run_gan_loop, render_cv_to_pdf
from backend.config import settings
from backend.services.groq_service import call_groq

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory SSE queues per company_id (process-local, lost on restart)
_status_queues: dict[str, asyncio.Queue] = {}


def get_queue(company_id: str) -> asyncio.Queue:
    if company_id not in _status_queues:
        _status_queues[company_id] = asyncio.Queue()
    return _status_queues[company_id]


async def broadcast_status(company_id: str, message: str):
    await get_queue(company_id).put(message)


async def _generation_workflow(company_id: str, doc_type: str):
    try:
        targets = json_store.read_targets()
        target = next((t for t in targets if t.company_id == company_id), None)
        if not target:
            raise ValueError("Target company not found.")

        profile = json_store.read_raw_profile()

        await broadcast_status(company_id, "🔍 Researching company and building HR persona...")
        persona = await research_company(company_id, target)

        await broadcast_status(company_id, "🧬 Starting GAN generation loop...")

        async def gan_progress_cb(msg: str):
            await broadcast_status(company_id, msg)

        gan_result = await run_gan_loop(
            company_id=company_id,
            profile=profile,
            persona=persona,
            doc_type=doc_type,
            progress_callback=gan_progress_cb,
            company_name=target.company_name,
        )

        await broadcast_status(company_id, "🎨 Rendering PDF...")
        target_dir = Path(settings.DATA_DIR) / "applications" / company_id
        pdf_path = target_dir / f"{doc_type}.pdf"
        await render_cv_to_pdf(gan_result["doc"], str(pdf_path), doc_type=doc_type)

        await broadcast_status(company_id, f"DONE|{gan_result['score']}")

    except Exception as e:
        logger.error(f"Generation workflow failed for {company_id}: {e}", exc_info=True)
        await broadcast_status(company_id, f"ERROR|{str(e)}")


# ── Trigger endpoints ──────────────────────────────────────────────────────

@router.post("/cv/generate/{company_id}")
async def generate_cv(company_id: str, background_tasks: BackgroundTasks):
    _status_queues[company_id] = asyncio.Queue()
    background_tasks.add_task(_generation_workflow, company_id, "cv")
    return {"status": "started", "company_id": company_id, "doc_type": "cv"}


@router.post("/cover-letter/generate/{company_id}")
async def generate_cl(company_id: str, background_tasks: BackgroundTasks):
    _status_queues[company_id] = asyncio.Queue()
    background_tasks.add_task(_generation_workflow, company_id, "cover_letter")
    return {"status": "started", "company_id": company_id, "doc_type": "cover_letter"}


# ── SSE stream ─────────────────────────────────────────────────────────────

@router.get("/status/{company_id}")
async def stream_status(company_id: str):
    q = get_queue(company_id)

    async def event_generator():
        try:
            while True:
                message = await q.get()
                yield f"data: {message}\n\n"
                if message.startswith("DONE|") or message.startswith("ERROR|"):
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── PDF file endpoints ──────────────────────────────────────────────────────

def _get_pdf_response(pdf_path: Path, filename: str) -> FileResponse:
    """Serve a PDF inline — raises 404 if missing or empty (corrupted)."""
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found. Run generation first.")
    if pdf_path.stat().st_size == 0:
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF file is empty (rendering failed). "
                "Check logs and ensure `playwright install chromium` has been run."
            )
        )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )


@router.get("/cv/{company_id}")
async def get_cv_pdf(company_id: str):
    pdf_path = Path(settings.DATA_DIR) / "applications" / company_id / "cv.pdf"
    return _get_pdf_response(pdf_path, f"CV_{company_id}.pdf")


@router.get("/cover-letter/{company_id}")
async def get_cl_pdf(company_id: str):
    pdf_path = Path(settings.DATA_DIR) / "applications" / company_id / "cover_letter.pdf"
    return _get_pdf_response(pdf_path, f"CoverLetter_{company_id}.pdf")


# ── JSON read / edit ────────────────────────────────────────────────────────

@router.get("/cv/json/{company_id}")
async def get_cv_json(company_id: str):
    json_path = Path(settings.DATA_DIR) / "applications" / company_id / "cv.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="CV JSON not found.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.patch("/cv/{company_id}")
async def update_cv(company_id: str, cv_json: dict):
    target_dir = Path(settings.DATA_DIR) / "applications" / company_id
    json_path = target_dir / "cv.json"
    pdf_path = target_dir / "cv.pdf"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cv_json, f, indent=2)
    await render_cv_to_pdf(cv_json, str(pdf_path), doc_type="cv")
    return {"status": "updated"}


@router.post("/cv/optimize")
async def optimize_cv(cv_json: dict):
    prompt_path = Path("backend/prompts/cv_optimize.txt")
    if not prompt_path.exists():
        raise HTTPException(status_code=500, detail="Optimization prompt not found.")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    system_prompt = "You are an ATS optimization engine. Return valid JSON only."
    user_message = prompt_template.replace("{{cv_json}}", json.dumps(cv_json, indent=2))
    try:
        return await call_groq(
            system_prompt=system_prompt,
            user_message=user_message,
            expect_json=True,
            purpose="optimize_cv_ats"
        )
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cover-letter/json/{company_id}")
async def get_cl_json(company_id: str):
    json_path = Path(settings.DATA_DIR) / "applications" / company_id / "cover_letter.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Cover Letter JSON not found.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.patch("/cover-letter/{company_id}")
async def update_cl(company_id: str, cl_json: dict):
    target_dir = Path(settings.DATA_DIR) / "applications" / company_id
    json_path = target_dir / "cover_letter.json"
    pdf_path = target_dir / "cover_letter.pdf"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cl_json, f, indent=2)
    await render_cv_to_pdf(cl_json, str(pdf_path), doc_type="cover_letter")
    return {"status": "updated"}


# ── Research / scoring transparency endpoints ───────────────────────────────

@router.get("/meta/{company_id}")
async def get_application_meta(company_id: str):
    """Returns persona, scraped data, and target info for a company."""
    meta_path = Path(settings.DATA_DIR) / "applications" / company_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Research data not found. Run generation first.")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/iterations/{company_id}")
async def get_gan_iterations(company_id: str):
    """Returns the GAN loop scoring history for a company's CV."""
    iter_path = Path(settings.DATA_DIR) / "applications" / company_id / "cv_iterations.json"
    if not iter_path.exists():
        return []
    with open(iter_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/explain/{company_id}")
async def explain_insight(company_id: str, body: dict):
    """Return an AI explanation of why a specific insight was identified, grounded in the job posting."""
    insight_type = body.get("insight_type", "")
    insight_value = body.get("insight_value", "")

    meta_path = Path(settings.DATA_DIR) / "applications" / company_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Research data not found. Run generation first.")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    job_text = (meta.get("scraped_data") or {}).get("job_posting_text", "")
    company_info = meta.get("company_info") or {}
    persona = meta.get("persona") or {}

    is_scoring_note = insight_type == "scoring_note"

    json_schema = (
        '{"term_definition":"string","why_identified":"string",'
        '"source_quote":"string","what_it_means":"string","priority":"high|medium|low"}'
    )

    if is_scoring_note:
        system_prompt = (
            "You are an AI assistant explaining CV scoring feedback to a job applicant. "
            "Given a specific piece of feedback from an HR evaluator, explain what it means "
            "and give the candidate a concrete way to fix it for this exact role and company.\n\n"
            f"Return ONLY valid JSON: {json_schema}\n"
            'Set term_definition to "" and source_quote to "" for scoring notes. '
            "Write plainly. No buzzwords. Short sentences."
        )
    else:
        system_prompt = (
            "You are an AI research assistant explaining hiring insights to a job applicant. "
            "Given a specific keyword or insight and the job posting it came from, produce four things:\n\n"
            "1. term_definition: Define the keyword in plain English (1-2 sentences). "
            "If it is corporate jargon or a technical concept (e.g. 'ownership', 'bias-for-action', "
            "'cross-functional', 'stakeholder management'), explain what it actually means in practice — "
            "no jargon in the definition itself. If the term is already obvious everyday language, set this to \"\".\n"
            "2. why_identified: What specifically in the job posting or company data led the AI to flag this keyword. "
            "Be concrete — name the signal (job title, requirement, company culture note, etc.).\n"
            "3. source_quote: An exact short excerpt (5-25 words) from the job posting that is the primary source. "
            "Empty string if unavailable.\n"
            "4. what_it_means: One concrete action the candidate should take for this specific role and company. "
            "Start with a verb. One sentence max.\n"
            "5. priority: high | medium | low\n\n"
            f"Return ONLY valid JSON: {json_schema}\n"
            "Write plainly. No buzzwords in your explanations."
        )

    user_message = (
        f"Insight Type: {insight_type.replace('_', ' ')}\n"
        f"Insight: {insight_value}\n\n"
        f"Company: {company_info.get('company_name', 'Unknown')}\n"
        f"Role: {company_info.get('job_title', 'Unknown')}\n\n"
        f"Job Posting Text:\n{job_text[:2500] if job_text else '(not available)'}\n\n"
        f"Hiring Persona:\n{json.dumps(persona, indent=2)}"
    )

    try:
        return await call_groq(
            system_prompt=system_prompt,
            user_message=user_message,
            expect_json=True,
            purpose="explain_insight"
        )
    except Exception as e:
        logger.error(f"Insight explanation failed for {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
