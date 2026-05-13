import asyncio
import json
from pathlib import Path
import sys

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from backend.services.cv_service import render_cv_to_pdf

async def verify_rendering():
    print("Verifying PDF rendering using refactored cv_service...")
    
    mock_cv = {
        "header": {
            "name": "Zied Cherif",
            "email": "zied@example.com",
            "phone": "12345678",
            "location": "Tunisia",
            "links": ["https://linkedin.com/in/zied"]
        },
        "education": [
            {
                "institution": "University of Sfax",
                "degree": "Engineer's Degree",
                "date": "2018-2023",
                "gpa": "3.8"
            }
        ],
        "experience": [
            {
                "company": "TechCorp",
                "role": "Senior Developer",
                "date": "2023-Present",
                "bullet_points": [
                    "Led a team of 5 developers to build a scalable microservices architecture.",
                    "Improved API performance by 40% using Playwright and asynchronous processing."
                ]
            }
        ],
        "projects": [
            {
                "name": "Jobless.io",
                "description": "AI-powered job application automator.",
                "bullet_points": ["Automated resume tailoring", "Integrated OpenRouter for robust LLM interactions"]
            }
        ],
        "skills": ["Python", "FastAPI", "Playwright", "React"],
        "soft_skills": ["Leadership", "Problem Solving"]
    }
    
    output_path = "tests/test_final_cv.pdf"
    await render_cv_to_pdf(mock_cv, output_path)
    
    file_path = Path(output_path)
    if file_path.exists() and file_path.stat().st_size > 0:
        print(f"SUCCESS: {output_path} generated and is not empty ({file_path.stat().st_size} bytes).")
    else:
        print(f"FAILED: {output_path} is missing or empty.")

if __name__ == "__main__":
    asyncio.run(verify_rendering())
