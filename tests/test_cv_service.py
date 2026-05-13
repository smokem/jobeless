import tempfile
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock

from backend.services.cv_service import research_company, run_gan_loop, render_cv_to_pdf
from backend.models.schemas import TargetCompany, HiringPersona

# --- Mocks ---

MOCK_TARGET = TargetCompany(
    company_id="tgt_test",
    company_name="TestCorp",
    company_linkedin="https://linkedin.com/company/testcorp",
    job_title="Software Tester",
    job_url="https://linkedin.com/jobs/123",
    apply_type="easy_apply",
    location="Remote"
)

MOCK_PROFILE = {"personal_info": {"full_name": "Test User"}}

MOCK_PERSONA = HiringPersona(
    company_values=["Innovation", "Testing"],
    hr_communication_style="Direct",
    what_they_look_for=["Attention to detail"],
    red_flags_to_avoid=["Sloppy code"],
    cultural_keywords=["Quality"],
    tone_preference="technical"
)

MOCK_GENERATOR_JSON = {
    "header": {"name": "Test User", "headline": "Tester", "email": "test@test.com", "phone": "123", "location": "Remote", "links": []},
    "education": [],
    "experience": [],
    "projects": [],
    "skills": ["Python"],
    "soft_skills": ["Careful"]
}

# --- Tests ---

@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        with patch("backend.services.cv_service.settings.DATA_DIR", tmpdirname):
            yield tmpdirname


@pytest.mark.asyncio
@patch("backend.services.cv_service.scrape_company_profile")
@patch("backend.services.cv_service.call_groq")
async def test_research_company_flow(mock_groq, mock_scrape_comp, temp_data_dir):
    """Test full pipeline of scraping and persona synthesis."""
    mock_scrape_comp.return_value = {"about": "Test Data"}
    # Mock groq returning valid Persona JSON
    mock_groq.return_value = MOCK_PERSONA.model_dump(mode="json")
    
    persona = await research_company("tgt_test_1", MOCK_TARGET)
    
    assert persona.company_values[0] == "Innovation"
    mock_groq.assert_called_once()
    
    # Check if meta.json was written
    meta_path = os.path.join(temp_data_dir, "applications", "tgt_test_1", "meta.json")
    assert os.path.exists(meta_path)


@pytest.mark.asyncio
@patch("backend.services.cv_service.call_groq")
async def test_gan_loop_passes_on_second_try(mock_groq, temp_data_dir):
    """Test that the loop iterates correctly until score >= 9.0."""
    
    # We'll handle Groq calls for both Generator and Discriminator sequentially
    # Iter 1: Gen -> Score (7.0)
    # Iter 2: Gen -> Score (9.5)
    mock_groq.side_effect = [
        MOCK_GENERATOR_JSON, # Iter 1 Gen
        {"score": 7.0, "notes": ["Add more info"], "strengths": ["Good name"], "passed": False}, # Iter 1 Score
        MOCK_GENERATOR_JSON, # Iter 2 Gen
        {"score": 9.5, "notes": [], "strengths": ["Perfect"], "passed": True} # Iter 2 Score
    ]
    
    result = await run_gan_loop("tgt_123", MOCK_PROFILE, MOCK_PERSONA, "cv")
    
    assert result["score"] == 9.5
    assert len(result["iterations"]) == 2
    assert mock_groq.call_count == 4


@pytest.mark.asyncio
@patch("backend.services.cv_service.call_groq")
async def test_gan_loop_max_iterations(mock_groq, temp_data_dir):
    """Test loop stops at max iterations even if score never hits 9.0."""
    
    # 5 iterations * 2 calls per iteration (Gen + Score) = 10 calls
    responses = []
    for _ in range(5):
        responses.append(MOCK_GENERATOR_JSON)
        responses.append({"score": 8.0, "notes": ["Not quite"], "strengths": [], "passed": False})
        
    mock_groq.side_effect = responses
    
    result = await run_gan_loop("tgt_123", MOCK_PROFILE, MOCK_PERSONA, "cv")
    
    assert result["score"] == 8.0
    assert len(result["iterations"]) == 5
    assert mock_groq.call_count == 10
