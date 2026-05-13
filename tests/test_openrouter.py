import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from backend.services.groq_service import call_groq
from backend.config import settings

def test_openrouter():
    print(f"Testing OpenRouter with model: {settings.OPENROUTER_MODEL}")
    try:
        response = call_groq(
            system_prompt="You are a helpful assistant.",
            user_message="Say 'Verification Success' if you are working.",
            purpose="verification_test"
        )
        print(f"Response: {response}")
        if "Verification Success" in response:
            print("SUCCESS: OpenRouter is working correctly.")
        else:
            print("WARNING: OpenRouter responded but the content was unexpected.")
    except Exception as e:
        print(f"FAILED: OpenRouter call failed with error: {e}")

if __name__ == "__main__":
    test_openrouter()
