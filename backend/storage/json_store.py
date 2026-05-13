import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, List, Optional, Type, TypeVar
from pydantic import BaseModel, TypeAdapter
from backend.config import settings
from backend.models.schemas import (
    ProfileMeta, ApplicationHistory, TargetCompany, 
    ApplicationMeta, InterviewSession
)

# Setup logging for storage operations
logging.basicConfig(
    filename=settings.DEBUG_LOG,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

def write_json_atomic(path: Path, data: Any):
    """
    Writes data to a temporary file then renames it to the target path.
    This ensures atomic writes and prevents data corruption.
    """
    tmp_path = path.with_suffix(".tmp")
    try:
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        
        shutil.move(tmp_path, path)
        logger.info(f"Successfully wrote {path}")
    except Exception as e:
        logger.error(f"Failed to write {path}: {str(e)}")
        if tmp_path.exists():
            tmp_path.unlink()
        raise

def read_json(path: Path, model: Type[T]) -> T:
    """Reads JSON from path and validates against the provided Pydantic model."""
    try:
        if not path.exists():
            logger.warning(f"File not found: {path}")
            raise FileNotFoundError(f"File {path} does not exist.")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"Successfully read {path}")
        return model.model_validate(data)
    except Exception as e:
        logger.error(f"Error reading {path}: {str(e)}")
        raise

def read_json_list(path: Path, model: Type[T]) -> List[T]:
    """Reads a JSON list and validates each item against the Pydantic model."""
    try:
        if not path.exists():
            return []
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        adapter = TypeAdapter(List[model])
        logger.info(f"Successfully read list from {path}")
        return adapter.validate_python(data)
    except Exception as e:
        logger.error(f"Error reading list from {path}: {str(e)}")
        raise

# --- Specific Store Implementations ---

def read_raw_profile() -> dict:
    """Reads profile.json and returns the raw dict without Pydantic validation."""
    path = settings.PROFILE_FILE
    try:
        if not path.exists():
            logger.warning(f"File not found: {path}")
            raise FileNotFoundError(f"File {path} does not exist.")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Successfully read raw profile from {path}")
        return data
    except Exception as e:
        logger.error(f"Error reading raw profile from {path}: {str(e)}")
        raise

def write_profile(data: dict):
    """Writes profile data to profile.json using atomic write."""
    write_json_atomic(settings.PROFILE_FILE, data)

def read_profile() -> ProfileMeta:
    return read_json(settings.PROFILE_FILE, ProfileMeta)

def read_history() -> List[ApplicationHistory]:
    return read_json_list(settings.HISTORY_FILE, ApplicationHistory)

def write_history(data: List[ApplicationHistory]):
    json_data = [item.model_dump(mode='json') for item in data]
    write_json_atomic(settings.HISTORY_FILE, json_data)

def read_targets() -> List[TargetCompany]:
    return read_json_list(settings.TARGETS_FILE, TargetCompany)

def write_targets(data: List[TargetCompany]):
    json_data = [item.model_dump(mode='json') for item in data]
    write_json_atomic(settings.TARGETS_FILE, json_data)

def read_application_meta(company_id: str) -> ApplicationMeta:
    path = settings.APPLICATIONS_DIR / company_id / "meta.json"
    return read_json(path, ApplicationMeta)

def write_application_meta(company_id: str, data: ApplicationMeta):
    path = settings.APPLICATIONS_DIR / company_id / "meta.json"
    write_json_atomic(path, data.model_dump(mode='json'))

def read_interview_session(company_id: str, session_id: str) -> InterviewSession:
    path = settings.INTERVIEW_SESSIONS_DIR / company_id / f"{session_id}.json"
    return read_json(path, InterviewSession)

def write_interview_session(company_id: str, session_id: str, data: InterviewSession):
    path = settings.INTERVIEW_SESSIONS_DIR / company_id / f"{session_id}.json"
    write_json_atomic(path, data.model_dump(mode='json'))
