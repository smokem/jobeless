import asyncio
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from backend.storage import json_store
from backend.services.cv_service import research_company, run_gan_loop, render_cv_to_pdf
from backend.models.schemas import TargetCompany, ApplicationMeta
from backend.config import settings

import logging
from backend.services.groq_service import call_groq

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory queues to handle per-company SSE streaming
# company_id -> asyncio.Queue
_status_queues = {}


def get_queue(company_id: str) -> asyncio.Queue:
    if company_id not in _status_queues:
        _status_queues[company_id] = asyncio.Queue()
    return _status_queues[company_id]


async def broadcast_status(company_id: str, message: str):
    """Utility to put messages to the company's SSE queue."""
    q = get_queue(company_id)
    await q.put(message)
    logger.info(f"[SSE Dispatch] {company_id}: {message}")


async def _generation_workflow(company_id: str, doc_type: str):
    """
    Background task wrapper that connects CV service to SSE progress reporting.
    """
    try:
        # 1. Load target and profile
        targets = json_store.read_targets()
        target = next((t for t in targets if t.company_id == company_id), None)
        if not target:
            raise ValueError("Target company not found.")
            
        profile = json_store.read_raw_profile()
        
        # 2. Research Target Phase
        await broadcast_status(company_id, "🔍 Researching company...")
        persona = await research_company(company_id, target)
        
        # 3. GAN Loop Phase
        await broadcast_status(company_id, "🧬 Building HR persona...")
        
        async def gan_progress_cb(msg: str):
            await broadcast_status(company_id, msg)
            
        gan_result = await run_gan_loop(
            company_id=company_id, 
            profile=profile, 
            persona=persona, 
            doc_type=doc_type,
            progress_callback=gan_progress_cb
        )
        
        # 4. Render PDF Phase
        await broadcast_status(company_id, "🎨 Rendering professional PDF...")
        target_dir = Path(settings.DATA_DIR) / "applications" / company_id
        pdf_path = target_dir / f"{doc_type}.pdf"
        await render_cv_to_pdf(gan_result["doc"], str(pdf_path))
        
        # Done
        await broadcast_status(company_id, f"DONE|{gan_result['score']}")
        
    except Exception as e:
        logger.error(f"Generation workflow failed for {company_id}: {e}")
        await broadcast_status(company_id, f"ERROR|{str(e)}")


@router.post("/cv/generate/{company_id}")
async def generate_cv(company_id: str, background_tasks: BackgroundTasks):
    """Triggers the async background process to research and build the CV."""
    # Reset queue for clean state
    if company_id in _status_queues:
        _status_queues[company_id] = asyncio.Queue()
        
    background_tasks.add_task(_generation_workflow, company_id, "cv")
    return {"status": "started", "company_id": company_id, "doc_type": "cv"}


@router.post("/cover-letter/generate/{company_id}")
async def generate_cl(company_id: str, background_tasks: BackgroundTasks):
    """Triggers the async background process for the cover letter."""
    if company_id in _status_queues:
        _status_queues[company_id] = asyncio.Queue()
        
    background_tasks.add_task(_generation_workflow, company_id, "cover_letter")
    return {"status": "started", "company_id": company_id, "doc_type": "cover_letter"}


@router.get("/status/{company_id}")
async def stream_status(company_id: str):
    """SSE endpoint for live status."""
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


@router.get("/cv/{company_id}")
async def get_cv_pdf(company_id: str):
    """Returns the generated CV PDF."""
    pdf_path = Path(settings.DATA_DIR) / "applications" / company_id / "cv.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="CV PDF not found.")
    return FileResponse(
        path=pdf_path, 
        media_type="application/pdf", 
        filename=f"CV_{company_id}.pdf",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@router.get("/cover-letter/{company_id}")
async def get_cl_pdf(company_id: str):
    """Returns the generated Cover Letter PDF."""
    pdf_path = Path(settings.DATA_DIR) / "applications" / company_id / "cover_letter.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Cover Letter PDF not found.")
    return FileResponse(
        path=pdf_path, 
        media_type="application/pdf", 
        filename=f"CoverLetter_{company_id}.pdf",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )
@router.get("/cv/json/{company_id}")
async def get_cv_json(company_id: str):
    """Returns the raw CV JSON."""
    json_path = Path(settings.DATA_DIR) / "applications" / company_id / "cv.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="CV JSON not found.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.patch("/cv/{company_id}")
async def update_cv(company_id: str, cv_json: dict):
    """Updates the CV JSON and re-renders the PDF."""
    target_dir = Path(settings.DATA_DIR) / "applications" / company_id
    json_path = target_dir / "cv.json"
    pdf_path = target_dir / "cv.pdf"
    
    # Update JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cv_json, f, indent=2)
        
    # Re-render PDF - ensure we use the PASSED cv_json, not reading from disk immediately
    await render_cv_to_pdf(cv_json, str(pdf_path))
    return {"status": "updated"}


@router.post("/cv/optimize")
async def optimize_cv(cv_json: dict):
    """Sends the CV JSON to LLM for ATS optimization and unknown filling."""
    prompt_path = Path("backend/prompts/cv_optimize.txt")
    if not prompt_path.exists():
        raise HTTPException(status_code=500, detail="Optimization prompt not found.")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    system_prompt = "You are an ATS optimization engine. Return valid JSON only."
    user_message = prompt_template.replace("{{cv_json}}", json.dumps(cv_json, indent=2))
    
    try:
        optimized_json = await call_groq(
            system_prompt=system_prompt,
            user_message=user_message,
            expect_json=True,
            purpose="optimize_cv_ats"
        )
        return optimized_json
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cover-letter/json/{company_id}")
async def get_cl_json(company_id: str):
    """Returns the raw Cover Letter JSON."""
    json_path = Path(settings.DATA_DIR) / "applications" / company_id / "cover_letter.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Cover Letter JSON not found.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.patch("/cover-letter/{company_id}")
async def update_cl(company_id: str, cl_json: dict):
    """Updates the Cover Letter JSON and re-renders the PDF."""
    target_dir = Path(settings.DATA_DIR) / "applications" / company_id
    json_path = target_dir / "cover_letter.json"
    pdf_path = target_dir / "cover_letter.pdf"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cl_json, f, indent=2)
        
    await render_cv_to_pdf(cl_json, str(pdf_path)) # render_cv_to_pdf is generic enough for CL too
    return {"status": "updated"}
