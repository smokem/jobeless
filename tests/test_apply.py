import pytest
from unittest.mock import patch, MagicMock

from backend.routers.apply import apply_to_target, get_status
from backend.models.schemas import TargetCompany, ApplicationHistory
from fastapi import HTTPException
from datetime import datetime

# --- Mocks ---

MOCK_TARGET = TargetCompany(
    company_id="tgt_test_apply",
    company_name="TestingApplyCorp",
    company_linkedin="https://linkedin.com/company/testapplycorp",
    job_title="Automation Engineer",
    job_url="https://linkedin.com/jobs/123",
    apply_type="easy_apply",
    location="Remote",
    status="pending"
)

# --- Tests ---

def test_get_status():
    """Verify limit checks return correct constraints."""
    with patch("backend.routers.apply.json_store.read_history") as mock_history:
        mock_history.return_value = []
        with patch("backend.routers.apply.json_store.read_targets") as mock_targets:
            mock_targets.return_value = [MOCK_TARGET]
            
            res = get_status()
            
            assert res["sent_today"] == 0
            assert res["pending_targets"] == 1
            assert res["max_limit"] == 20

@pytest.mark.asyncio
@patch("backend.routers.apply.json_store.write_history")
@patch("backend.routers.apply.json_store.write_targets")
@patch("backend.routers.apply.json_store.read_history")
@patch("backend.routers.apply.json_store.read_targets")
@patch("backend.routers.apply.Path.exists")
@patch("backend.routers.apply.easy_apply")
async def test_apply_to_target_success(mock_easy_apply, mock_exists, mock_rt, mock_rh, mock_wt, mock_wh):
    """Test successful application using easy_apply Playwright service."""
    mock_rt.return_value = [MOCK_TARGET]
    mock_rh.return_value = []
    mock_exists.return_value = True # Pretend CV PDF exists
    mock_easy_apply.return_value = {"success": True, "method": "easy_apply"}
    
    result = await apply_to_target("tgt_test_apply")
    
    assert result["success"] == True
    mock_easy_apply.assert_called_once()
    mock_wh.assert_called_once()
    mock_wt.assert_called_once()
    
    # Check that history update reflects 'sent' status
    history_args = mock_wh.call_args[0][0]
    assert len(history_args) == 1
    assert history_args[0].status == "sent"

@pytest.mark.asyncio
@patch("backend.routers.apply.json_store.read_history")
async def test_daily_limit_rejection(mock_rh):
    """Verify application gracefully refuses to start if daily max limit is reached."""
    # Build 20 fake histories for today
    today_histories = [
       ApplicationHistory(
           company_id=f"t_{i}", company_name="Test", job_title="Job",
           date_sent=datetime.now(), apply_method="easy_apply",
           cv_score_achieved=9.0, status="sent", cv_path="", cl_path=""
       ) for i in range(20)
    ]
    mock_rh.return_value = today_histories
    
    with pytest.raises(HTTPException) as excinfo:
        await apply_to_target("tgt_test_apply")
        
    assert excinfo.value.status_code == 429
    assert "Daily limit" in str(excinfo.value.detail)
