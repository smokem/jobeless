import asyncio
import json
from pathlib import Path
import sys

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from backend.services.cv_service import render_cv_to_pdf

async def verify_new_layout():
    print("Verifying new PDF layout with profile picture and guessing unknowns...")
    
    # Mock CV JSON with "Unknown" values that should ideally have been fixed by LLM, 
    # but we simulate the renderer's ability to handle the data I just added.
    mock_cv = {
        "header": {
            "name": "Zied Cherif",
            "headline": "Designer | Developer | Machine Learning Enthusiast",
            "email": "czied30@gmail.com",
            "phone": "+21624432602",
            "location": "Sfax, Tunisia",
            "links": ["https://linkedin.com/in/ziedcherif", "https://github.com/zcherif-coder"],
            "profile_picture": "https://media.licdn.com/dms/image/v2/D4D03AQFd_IJeYpiO0w/profile-displayphoto-shrink_800_800/B4DZUYIaZbHwAc-/0/1739866614476?e=1779321600&v=beta&t=hY7EdMkA0ze0G6BIRH2IXBqpeHbVD8SgIQA3o2CBuU8"
        },
        "education": [
            {
                "institution": "Institut International de Technologie",
                "degree": "Engineer's Degree",
                "date": "2022 - 2025 (Estimated)",
                "gpa": "3.5 (Estimated)"
            }
        ],
        "experience": [
            {
                "company": "Future Proof",
                "role": "Full Stack Developer",
                "date": "2025-07 - Present",
                "bullet_points": [
                    "Spearheaded the development of a high-performance Flutter mobile application, improving booking efficiency by 30%.",
                    "Architected scalable microservices using Spring Boot and Kubernetes, enhancing system reliability by a measurable 25%."
                ]
            }
        ],
        "projects": [
            {
                "name": "iPerson",
                "description": "An intelligent habit monitoring system leveraging Llama 2 and BERT.",
                "bullet_points": ["Achieved 95% satisfaction by humanizing AI interactions."]
            }
        ],
        "skills": ["React", "Python", "Playwright", "Microservices"],
        "soft_skills": ["Leadership", "Innovation"]
    }
    
    output_path = "tests/test_layout_v2.pdf"
    await render_cv_to_pdf(mock_cv, output_path)
    
    file_path = Path(output_path)
    if file_path.exists() and file_path.stat().st_size > 0:
        print(f"SUCCESS: {output_path} generated ({file_path.stat().st_size} bytes).")
    else:
        print(f"FAILED: {output_path} is missing or empty.")

if __name__ == "__main__":
    asyncio.run(verify_new_layout())
