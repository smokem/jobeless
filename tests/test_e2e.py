import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

@patch("backend.routers.discovery.call_groq")
@patch("backend.routers.discovery.scrape_linkedin_jobs")
@patch("backend.routers.generation.run_gan_loop")
@patch("backend.routers.apply.easy_apply")
@patch("backend.services.interview_service.call_groq")
@patch("backend.routers.apply.json_store.read_targets")
@patch("backend.routers.apply.json_store.read_history")
@patch("backend.routers.apply.json_store.write_history")
@patch("backend.routers.apply.json_store.write_targets")
@patch("backend.services.interview_service.json_store.read_application_meta")
@patch("backend.services.interview_service.json_store.write_interview_session")
@patch("backend.services.interview_service.json_store.read_interview_session")
def test_full_pipeline_e2e(
    mock_read_int, mock_write_int, mock_read_meta, 
    mock_write_targets, mock_write_history, mock_read_history, mock_read_targets, 
    mock_int_groq, mock_apply, mock_gan, mock_scrape, mock_disc_groq
):
    """
    Simulates the complete AutoApply lifecycle covering Discovery, Research, Generating, Applying, and Interviewing.
    """
    
    # 1. Profile Load
    res = client.get("/api/profile/completeness")
    assert res.status_code == 200
    
    # 2. Discovery
    mock_disc_groq.return_value = [{"role": "Software Engineer", "match_score": 0.95, "reasoning": "Fits"}]
    res = client.get("/api/discovery/suggest-roles")
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    # Scraping targets
    from backend.models.schemas import TargetCompany, ApplicationHistory
    test_target = TargetCompany(
        company_id="test_corp", company_name="TestCorp", job_title="SE", 
        job_url="url", apply_type="easy_apply", location="Remote", status="pending"
    )
    mock_scrape.return_value = [test_target.model_dump()]
    
    res = client.post("/api/discovery/scrape", json={"role": "SE", "location": "Remote", "radius_miles": 25})
    assert res.status_code in [200, 202] # Depending on if we mocked the background task or waited
    
    # 3. GAN Loop
    # Assumes background task is triggered perfectly
    mock_gan.return_value = {"status": "success", "iterations": 2, "final_score": 9.2, "fallback": False}
    res = client.post("/api/generation/test_corp/generate-cv")
    assert res.status_code == 202 # Background accepted
    
    # 4. Apply
    mock_read_targets.return_value = [test_target]
    mock_read_history.return_value = []
    mock_apply.return_value = {"success": True, "method": "easy_apply"}
    
    with patch("backend.routers.apply.Path.exists", return_value=True):
        res = client.post("/api/apply/run/test_corp")
        assert res.status_code == 200
        assert res.json()["success"] == True
        
    mock_write_history.assert_called()
    
    # 5. Interview Simulation
    # Create persistent stubs instead of mocking built-in file reads.
    import os, json
    from backend.config import settings
    os.makedirs(settings.DATA_DIR / "applications" / "test_corp", exist_ok=True)
    with open(settings.DATA_DIR / "applications" / "test_corp" / "cv.json", "w", encoding="utf-8") as f:
        json.dump({"skills": ["AI", "React"], "header": {"headline": "Dev"}}, f)

    from backend.models.schemas import ApplicationMeta, HiringPersona
    mock_read_meta.return_value = ApplicationMeta(company_id="test_corp", company_info=test_target, persona=HiringPersona(
        company_values=[], hr_communication_style="", what_they_look_for=[], red_flags_to_avoid=[], cultural_keywords=[], tone_preference=""
    ))
    
    mock_int_groq.side_effect = [
        "Welcome to the interview.", # Start session
        {"coaching_tip": "Be specific", "ideal_answer_structure": "A B C", "question_intent": "Testing you", "keywords_to_mention": []}, # Coach
        {"overall_score": 8.0, "categories": {}, "strengths": [], "improvements": [], "recommendation": "hire"} # Score
    ]
    
    # A. Start
    from backend.models.schemas import InterviewSession
    mock_read_int.return_value = InterviewSession(session_id="sim_123", company_id="test_corp", messages=[])
    
    with patch("backend.services.interview_service.uuid.uuid4", return_value="sim_123"):
       res = client.post("/api/interview/test_corp/start")
       assert res.status_code == 200
       assert res.json()["session_id"] == "sim_123"
    
    # B. Coach Help
    res = client.post("/api/interview/test_corp/sim_123/help")
    assert res.status_code == 200
    assert "coaching_tip" in res.json()
    
    # C. Score / End
    res = client.post("/api/interview/test_corp/sim_123/end")
    assert res.status_code == 200
    assert res.json()["recommendation"] == "hire"
