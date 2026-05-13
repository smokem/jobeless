import json
import pytest
from unittest.mock import patch, MagicMock

from backend.services.groq_service import call_groq
from backend.services.apify_service import scrape_linkedin_jobs
from backend.routers.discovery import scrape_jobs, suggest_roles

# --- Mock Data ---

MOCK_GROQ_RESPONSE = '''
```json
[
  {
    "role": "Frontend Developer",
    "match_score": 0.95,
    "reasoning": "Strong React and Vue experience."
  },
  {
    "role": "Full-Stack Developer",
    "match_score": 0.85,
    "reasoning": "Some backend experience with Node.js."
  }
]
```
'''

MOCK_APIFY_RESULTS = [
    {
        "title": "Frontend Developer",
        "companyName": "Tech Innovators",
        "companyUrl": "https://linkedin.com/company/tech-innovators",
        "url": "https://linkedin.com/jobs/001",
        "location": "Remote",
        "easyApply": True
    }
]

# --- Tests ---

@patch("backend.services.groq_service.groq_client")
def test_call_groq_json_parsing(mock_groq_client):
    """Test that call_groq correctly parses JSON and strips markdown fences."""
    # Setup mock
    mock_choice = MagicMock()
    mock_choice.message.content = MOCK_GROQ_RESPONSE
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_groq_client.chat.completions.create.return_value = mock_response

    # Test
    result = call_groq("System", "User", expect_json=True)
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["role"] == "Frontend Developer"
    assert result[0]["match_score"] == 0.95


@patch("backend.services.apify_service.apify_client")
@patch("backend.services.apify_service.settings")
def test_scrape_linkedin_jobs_mapping(mock_settings, mock_apify_client):
    """Test that Apify results are mapped to TargetCompany models."""
    mock_settings.APIFY_TOKEN = "valid_token"
    
    # Setup mock iterator
    mock_dataset = MagicMock()
    mock_dataset.iterate_items.return_value = MOCK_APIFY_RESULTS
    
    # Chain mocks: apify_client.actor().call() and apify_client.dataset()
    mock_apify_client.actor.return_value.call.return_value = {"defaultDatasetId": "dataset_123"}
    mock_apify_client.dataset.return_value = mock_dataset
    
    # Test
    targets = scrape_linkedin_jobs("Frontend", "Remote", 25)
    
    assert len(targets) == 1
    target = targets[0]
    assert target.company_name == "Tech Innovators"
    assert str(target.company_linkedin) == "https://linkedin.com/company/tech-innovators"
    assert str(target.job_url) == "https://linkedin.com/jobs/001"
    assert target.apply_type == "easy_apply"
    assert target.status == "pending"
