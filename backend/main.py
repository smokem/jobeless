import asyncio
import sys
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.routers import profile, discovery, generation, apply, history, interview
from backend.storage import json_store

# Setup logging
logging.basicConfig(
    filename=settings.DEBUG_LOG,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(
    title="AutoApply Platform API",
    description="Backend for the AutoApply job automation platform",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(discovery.router, prefix="/api/discovery", tags=["Discovery"])
app.include_router(generation.router, prefix="/api/generation", tags=["Generation"])
app.include_router(apply.router, prefix="/api/apply", tags=["Apply"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API and basic storage state."""
    profile_loaded = False
    try:
        json_store.read_profile()
        profile_loaded = True
    except Exception:
        pass
        
    return {
        "status": "ok",
        "profile_loaded": profile_loaded
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Logs unhandled exceptions and returns a structured error response."""
    logger.exception(f"Unhandled exception at {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if not isinstance(exc, RuntimeError) else "A server error occurred."
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
