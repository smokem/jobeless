import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Mocking settings and services
from backend.routers.generation import _generation_workflow

# Setup logging to console so we can see the tracebacks
logging.basicConfig(level=logging.INFO)

async def test_workflow():
    company_id = "tgt_1777922092_0_mock"
    doc_type = "cv"
    print(f"Testing full generation workflow for {company_id}...")
    await _generation_workflow(company_id, doc_type)
    
if __name__ == "__main__":
    asyncio.run(test_workflow())
