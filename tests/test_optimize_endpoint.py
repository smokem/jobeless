import requests
import json

def test_optimize():
    url = "http://localhost:8000/api/generation/cv/optimize"
    payload = {
        "header": {"name": "Zied Cherif", "email": "czied30@gmail.com"},
        "education": [{"institution": "IIT", "degree": "Unknown"}],
        "experience": [],
        "skills": ["Python"],
        "soft_skills": []
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_optimize()
