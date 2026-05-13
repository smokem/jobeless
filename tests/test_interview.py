import pytest
import asyncio
import uuid
import json
import os
from unittest.mock import patch, MagicMock

from backend.routers.interview import start_interview_endpoint, process_message_endpoint, get_help_endpoint, terminate_session_endpoint
from backend.models.schemas import InterviewSession, InterviewMessage, TargetCompany, HiringPersona, ApplicationMeta

# --- Mocks ---

MOCK_TARGET = TargetCompany(
    company_id="tgt_test_interview",
    company_name="SimCorp",
    company_linkedin="https://linkedin.com/company/simcorp",
    job_title="Simulation Engineer",
    job_url="https://linkedin.com/jobs/123",
    apply_type="easy_apply",
    location="Remote"
)

MOCK_PERSONA = HiringPersona(
    company_values=["Realism", "Agility"],
    hr_communication_style="Direct, strict",
    what_they_look_for=["Clear answers"],
    red_flags_to_avoid=["Rambling"],
    cultural_keywords=["Simulate"],
    tone_preference="formal"
)

MOCK_META = ApplicationMeta(
    company_id="tgt_test_interview",
    company_info=MOCK_TARGET,
    persona=MOCK_PERSONA
)

MOCK_SESSION = InterviewSession(
    session_id="sim_123",
    company_id="tgt_test_interview",
    messages=[
        InterviewMessage(role="system", content="Sys Prompt"),
        InterviewMessage(role="assistant", content="Hello, I am HR.")
    ]
)

@pytest.fixture
def mock_store_reads():
    with patch("backend.services.interview_service.json_store.read_application_meta", return_value=MOCK_META), \
         patch("backend.services.interview_service.open", new_callable=MagicMock) as mock_open_call, \
         patch("backend.services.interview_service.json.load", return_value={"skills": ["C++"]}), \
         patch("backend.services.interview_service.json_store.write_interview_session") as mock_write, \
         patch("backend.services.interview_service.json_store.read_interview_session", return_value=MOCK_SESSION):
        # We also mock open manually because json.load needs it
        mock_open_call.return_value.__enter__.return_value.read.return_value = "Prompt text"
        yield mock_write

@pytest.mark.asyncio
@patch("backend.services.interview_service.call_groq")
async def test_start_session(mock_groq, mock_store_reads):
    """Test start session reads context and invokes system prompt creation."""
    mock_groq.return_value = "Hello Zied, welcome."
    
    session = await start_interview_endpoint("tgt_test_interview")
    
    assert session["company_id"] == "tgt_test_interview"
    assert len(session["messages"]) == 2
    assert session["messages"][1]["content"] == "Hello Zied, welcome."
    mock_store_reads.assert_called_once()
    mock_groq.assert_called_once()

@pytest.mark.asyncio
@patch("backend.services.interview_service.call_groq")
async def test_send_message(mock_groq, mock_store_reads):
    """Verify standard message pingpong writes correctly without mutating context out of bounds."""
    mock_groq.return_value = "Great point. Next question?"
    
    result = await process_message_endpoint("tgt_test_interview", "sim_123", {"message": "I am great at C++."})
    
    assert result["reply"] == "Great point. Next question?"
    mock_store_reads.assert_called_once()

@pytest.mark.asyncio
@patch("backend.services.interview_service.call_groq")
async def test_coach_get_help(mock_groq, mock_store_reads):
    """Verify coach JSON is passed cleanly down."""
    mock_coaching_res = {
        "coaching_tip": "Be calm",
        "ideal_answer_structure": "1, 2, 3",
        "question_intent": "stress test",
        "keywords_to_mention": ["scale"]
    }
    mock_groq.return_value = mock_coaching_res
    
    res = await get_help_endpoint("tgt_test_interview", "sim_123")
    
    assert res["coaching_tip"] == "Be calm"
    # Make sure we don't accidentally write the coach prompt to the main convo log
    mock_store_reads.assert_not_called()

@pytest.mark.asyncio
@patch("backend.services.interview_service.call_groq")
async def test_end_session_scoring(mock_groq, mock_store_reads):
    """Ensure session wrap properly evaluates overall scores and terminates instance visually."""
    mock_eval = {
        "overall_score": 8.5,
        "categories": {},
        "strengths": ["test"],
        "improvements": ["test"],
        "recommendation": "hire"
    }
    mock_groq.return_value = mock_eval
    
    res = await terminate_session_endpoint("tgt_test_interview", "sim_123")
    
    assert res["overall_score"] == 8.5
    assert res["recommendation"] == "hire"
    mock_store_reads.assert_called_once() # Should update session with performance_score
