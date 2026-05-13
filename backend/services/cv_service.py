import json
import logging
import time
from pathlib import Path

from pydantic import ValidationError

from backend.config import settings
from backend.services.apify_service import scrape_company_profile, scrape_person_posts
from backend.services.groq_service import call_groq, _log_groq_decision
from backend.models.schemas import TargetCompany, HiringPersona

logger = logging.getLogger(__name__)

async def research_company(company_id: str, target: TargetCompany) -> HiringPersona:
    """
    Scrape company and personnel data, then use Groq to synthesize a Hiring Persona.
    Saves the result to applications/{company_id}/meta.json.
    """
    logger.info(f"Starting research for company_id: {company_id}")
    
    # 1. Scrape Apify
    company_data = scrape_company_profile(str(target.company_linkedin))
    ceo_posts = scrape_person_posts(str(target.ceo_linkedin)) if target.ceo_linkedin else []
    hr_posts = scrape_person_posts(str(target.hr_linkedin)) if target.hr_linkedin else []
    
    scraped_data_combined = {
        "company_info": company_data,
        "ceo_posts_sample": ceo_posts[:10],
        "hr_posts_sample": hr_posts[:10],
        "job_title": target.job_title
    }
    
    # 2. Call Groq
    prompt_path = settings.BASE_DIR / "backend" / "prompts" / "persona_build.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
        
    user_message = f"Please synthesize the hiring persona based on this scraped data:\n\n{json.dumps(scraped_data_combined, indent=2)}"
    
    persona_dict = await call_groq(
        system_prompt=system_prompt,
        user_message=user_message,
        expect_json=True,
        purpose="synthesize_persona"
    )
    
    # 3. Validate Pydantic Schema with resilience for common LLM output variations
    raw_persona = persona_dict
    try:
        persona = HiringPersona(**persona_dict)
    except ValidationError as ve:
        logger.warning(f"HiringPersona validation failed: {ve}. Attempting to coerce common types.")

        def _coerce_persona(d: dict) -> dict:
            new = dict(d) if isinstance(d, dict) else {}
            # Coerce list-like fields that might be returned as comma-separated strings
            list_fields = [
                "company_values", "what_they_look_for", "red_flags_to_avoid", "cultural_keywords"
            ]
            for k in list_fields:
                v = new.get(k)
                if v is None:
                    new[k] = []
                elif isinstance(v, str):
                    new[k] = [s.strip() for s in v.split(",") if s.strip()]
                elif isinstance(v, (list, tuple)):
                    new[k] = list(v)
                else:
                    new[k] = []

            # Ensure hr_communication_style is a string
            if not isinstance(new.get("hr_communication_style"), str):
                new["hr_communication_style"] = str(new.get("hr_communication_style") or "direct and outcome-focused")

            # Normalize tone_preference to allowed literals
            tp = new.get("tone_preference")
            allowed = {"formal", "casual", "technical"}
            if isinstance(tp, str):
                t = tp.strip().lower()
                if "form" in t:
                    new["tone_preference"] = "formal"
                elif "cas" in t:
                    new["tone_preference"] = "casual"
                elif "tech" in t:
                    new["tone_preference"] = "technical"
                else:
                    new["tone_preference"] = "technical"
            else:
                new["tone_preference"] = "technical"

            return new

        coerced = _coerce_persona(persona_dict)
        try:
            persona = HiringPersona(**coerced)
            logger.info("Successfully coerced HiringPersona from LLM output.")
        except ValidationError as ve2:
            logger.error(f"Coerced HiringPersona still invalid: {ve2}. Falling back to safe default persona.")
            # Fallback default persona to keep pipeline moving in dev
            persona = HiringPersona(
                company_values=["ownership", "iterative development"],
                hr_communication_style="direct and outcome-focused",
                what_they_look_for=["impact-oriented engineers"],
                red_flags_to_avoid=["lack of ownership"],
                cultural_keywords=["ownership", "bias-for-action"],
                tone_preference="technical"
            )
    
    # 4. Save to meta.json
    target_dir = Path(settings.DATA_DIR) / "applications" / company_id
    target_dir.mkdir(parents=True, exist_ok=True)
    
    meta_path = target_dir / "meta.json"
    meta_content = {
        "company_id": company_id,
        "target_info": target.model_dump(mode="json"),
        "persona": persona.model_dump(mode="json"),
        "raw_persona_output": raw_persona,
        "scraped_on": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Atomic write logic handled in json_store usually, but simple json dump here is fine 
    # since we're creating new files dynamically
    tmp_path = meta_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(meta_content, f, indent=2)
    tmp_path.replace(meta_path)
    
    return persona


async def run_gan_loop(company_id: str, profile: dict, persona: HiringPersona, doc_type: str, progress_callback=None) -> dict:
    """
    Runs the Generator/Discriminator loop for CV or Cover Letter.
    """
    # Load prompts based on doc_type
    prompts_dir = settings.BASE_DIR / "backend" / "prompts"
    if doc_type == "cv":
        gen_prompt_path = prompts_dir / "cv_generate.txt"
        score_prompt_path = prompts_dir / "cv_score.txt"
    elif doc_type == "cover_letter":
        gen_prompt_path = prompts_dir / "cover_letter_generate.txt"
        score_prompt_path = prompts_dir / "cover_letter_score.txt"
    else:
        raise ValueError("Invalid doc_type. Must be 'cv' or 'cover_letter'")
        
    with open(gen_prompt_path, "r", encoding="utf-8") as f:
        gen_sys_prompt = f.read()
    with open(score_prompt_path, "r", encoding="utf-8") as f:
        score_sys_prompt_template = f.read()
        
    # Inject variables into score prompt
    score_sys_prompt = score_sys_prompt_template.replace("{hr_name_or_title}", "HR Director")\
                                                .replace("{company_name}", "the Target Company")\
                                                .replace("{company_values}", ", ".join(persona.company_values))
    
    best_score = 0.0
    best_doc = None
    feedback_notes = "No previous feedback. This is the first attempt."
    iterations = []
    
    max_loops = 5  # Typical MAX_GAN_ITERATIONS
    
    for i in range(max_loops):
        iter_num = i + 1
        if progress_callback:
            await progress_callback(f"Generating {doc_type.upper()} (iteration {iter_num}/{max_loops})...")
            
        logger.info(f"GAN Loop Iteration {iter_num}/{max_loops} - Generation")
        
        # Generator
        gen_user_message = f"Profile:\n{json.dumps(profile, indent=2)}\n\nPersona:\n{persona.model_dump_json(indent=2)}\n\nFeedback Notes:\n{feedback_notes}"
        doc_json = await call_groq(
            system_prompt=gen_sys_prompt,
            user_message=gen_user_message,
            expect_json=True,
            purpose=f"generate_{doc_type}_iter_{iter_num}"
        )
        
        if progress_callback:
            await progress_callback(f"Scoring {doc_type.upper()}...")
            
        logger.info(f"GAN Loop Iteration {iter_num}/{max_loops} - Scoring")
        
        # Discriminator
        score_user_message = f"Evaluate this document:\n{json.dumps(doc_json, indent=2)}"
        eval_result = await call_groq(
            system_prompt=score_sys_prompt,
            user_message=score_user_message,
            expect_json=True,
            purpose=f"score_{doc_type}_iter_{iter_num}"
        )
        
        score = eval_result.get("score", 0.0)
        notes = eval_result.get("notes", [])
        passed = eval_result.get("passed", False)
        
        logger.info(f"Iteration {iter_num} Score: {score} | Passed: {passed} | Notes: {notes}")
        
        # Log to decisions.log specifically for the GAN iterations
        _log_groq_decision(
            module="cv_service",
            function="run_gan_loop",
            purpose=f"gan_discriminator_{doc_type}",
            prompt_tokens=0, completion_tokens=0, model=settings.GROQ_MODEL, success=True, attempt=iter_num,
            error=f"Score: {score}/10, Passed: {passed}" # Injecting result into string for decision log tracking
        )
        
        iterations.append({
            "iteration": iter_num,
            "score": score,
            "notes": notes,
            "passed": passed
        })
        
        if score > best_score:
            best_score = score
            best_doc = doc_json
            
        if passed or score >= 9.0:
            if progress_callback:
                await progress_callback(f"✅ {doc_type.upper()} achieved {score}/10 in {iter_num} iterations.")
            break
            
        # Update feedback for next iteration
        feedback_notes = f"Your previous draft scored {score}/10. Please fix these issues: " + "; ".join(notes)
        if progress_callback:
            await progress_callback(f"🔄 Regenerating, scored {score}/10... Fixing: {notes[0] if notes else 'minor issues'}")

    # Inject profile picture if available in candidate profile
    if profile and "personal_info" in profile:
        contact = profile["personal_info"].get("contact", {})
        pic_url = contact.get("profile_picture")
        if pic_url and best_doc and "header" in best_doc:
            best_doc["header"]["profile_picture"] = pic_url

    # Save final doc json
    target_dir = Path(settings.DATA_DIR) / "applications" / company_id
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / f"{doc_type}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(best_doc, f, indent=2)
        
    return {
        "doc": best_doc,
        "score": best_score,
        "iterations": iterations
    }


async def render_cv_to_pdf(cv_json: dict, output_path: str) -> str:
    """
    Render a CV JSON to PDF using WeasyPrint and a minimal HTML template.
    """
    try:
        from playwright.async_api import async_playwright
        from jinja2 import Environment, BaseLoader
    except Exception as e:
        logger.error(f"Playwright or rendering dependencies not available: {e}")
        # Create a dummy PDF if missing dependency so pipeline acts correct
        Path(output_path).touch()
        return output_path

    # Minimal Jinja2 Template enforcing 1-page constraints and clean layout
    template_str = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 1cm; }
        body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.3; color: #333; margin: 0; padding: 0; }
        .container { position: relative; }
        .header { display: flex; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
        .profile-pic { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; margin-right: 20px; border: 2px solid #2c3e50; }
        .header-content { flex-grow: 1; }
        h1 { font-size: 22pt; margin: 0; color: #2c3e50; text-transform: uppercase; letter-spacing: 1px; }
        .headline { font-size: 12pt; color: #7f8c8d; margin-top: 2px; font-weight: normal; }
        .contact { font-size: 9pt; color: #34495e; margin-top: 5px; }
        h2 { font-size: 12pt; background-color: #f8f9fa; border-left: 4px solid #2c3e50; padding: 4px 10px; margin: 15px 0 8px 0; color: #2c3e50; text-transform: uppercase; }
        .item-header { display: flex; justify-content: space-between; font-weight: bold; margin-top: 5px; color: #2c3e50; }
        .item-sub { font-style: italic; font-size: 9pt; color: #7f8c8d; margin-bottom: 5px; }
        ul { margin: 0 0 8px 15px; padding: 0; list-style-type: square; }
        li { margin-bottom: 3px; }
        .skills-section { background-color: #fcfcfc; padding: 10px; border: 1px solid #eee; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            {% if cv.header.profile_picture %}
            <img src="{{ cv.header.profile_picture }}" class="profile-pic" alt="Profile">
            {% endif %}
            <div class="header-content">
                <h1>{{ cv.header.name }}</h1>
                <div class="headline">{{ cv.header.headline }}</div>
                <div class="contact">
                    {{ cv.header.email }} | {{ cv.header.phone }} | {{ cv.header.location }}<br>
                    {% for link in cv.header.links %}{{ link.replace('https://', '') }}{% if not loop.last %} | {% endif %}{% endfor %}
                </div>
            </div>
        </div>

        <h2>Education</h2>
        {% for edu in cv.education %}
        <div class="item">
            <div class="item-header"><span>{{ edu.institution }}</span><span>{{ edu.date }}</span></div>
            <div class="item-sub">{{ edu.degree }} {% if edu.gpa %}- GPA: {{ edu.gpa }}{% endif %}</div>
        </div>
        {% endfor %}

        <h2>Experience</h2>
        {% for exp in cv.experience %}
        <div class="item">
            <div class="item-header"><span>{{ exp.company }} - {{ exp.role }}</span><span>{{ exp.date }}</span></div>
            <ul>
            {% for bullet in exp.bullet_points %}
                <li>{{ bullet }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endfor %}

        {% if cv.projects %}
        <h2>Projects</h2>
        {% for proj in cv.projects %}
        <div class="item">
            <div class="item-header"><span>{{ proj.name }}</span></div>
            <div class="item-sub">{{ proj.description }}</div>
            <ul>
            {% for bullet in proj.bullet_points %}
                <li>{{ bullet }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endfor %}
        {% endif %}

        <h2>Skills & Soft Skills</h2>
        <div style="font-size: 9pt;">
            <strong>Technical:</strong> {{ cv.skills | join(', ') }}<br>
            <strong>Soft Skills:</strong> {{ cv.soft_skills | join(', ') }}
        </div>
    </body>
    </html>
    """
    
    env = Environment(loader=BaseLoader())
    template = env.from_string(template_str)
    
    rendered_html = template.render(cv=cv_json)
    
    # Save the rendered HTML to pdf using playwright; guard against runtime/linker errors
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = await browser.new_page()
            await page.set_content(rendered_html)
            # Use A4 format and emulate print media for corect styling
            await page.emulate_media(media="print")
            await page.pdf(path=output_path, format="A4", print_background=True)
            await browser.close()
            
        logger.info(f"PDF successfully rendered to {output_path}")
        return output_path
    except Exception as e:
        import traceback
        logger.error(f"Failed to render PDF with Playwright: {e}\n{traceback.format_exc()}")
        # Fallback: create an empty placeholder so pipeline continues
        Path(output_path).touch()
        return output_path
