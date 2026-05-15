import uuid
from pathlib import Path
import json
import logging

from backend.config import settings
from backend.storage import json_store
from backend.models.schemas import InterviewSession, InterviewMessage
from backend.services.groq_service import call_groq

logger = logging.getLogger(__name__)

async def start_session(company_id: str) -> InterviewSession:
    """Initialize a new interview session and fetch opening question."""
    logger.info(f"Starting interview session for {company_id}")
    meta = json_store.read_application_meta(company_id)
    target = meta.company_info
    persona = meta.persona
    
    cv_path = Path(settings.DATA_DIR) / "applications" / company_id / "cv.json"
    with open(cv_path, "r", encoding="utf-8") as f:
        cv_data = json.load(f)
        
    sk = cv_data.get('skills', [])
    cv_key_points = f"Key Skills: {', '.join(sk)}. Headline: {cv_data.get('header', {}).get('headline', '')}."
    
    prompt_path = settings.BASE_DIR / "backend" / "prompts" / "interview_simulate.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_tmpl = f.read()
        
    system_prompt = prompt_tmpl.format(
        hr_name=target.hr_name or "Alex from Hiring Team",
        company_name=target.company_name,
        job_title=target.job_title,
        hr_communication_style=persona.hr_communication_style,
        what_they_look_for=", ".join(persona.what_they_look_for),
        red_flags_to_avoid=", ".join(persona.red_flags_to_avoid),
        tone_preference=persona.tone_preference,
        cv_key_points=cv_key_points
    )
    
    session_id = str(uuid.uuid4())
    
    # Generate the Opening statement
    ai_first_msg = await call_groq(
        system_prompt=system_prompt,
        user_message="[SYSTEM]: Start the interview seamlessly. Introduce yourself natively.",
        expect_json=False,
        purpose=f"interview_start_{session_id}"
    )
    
    # role 'system' acts as state keeping prompt base.
    messages = [
        InterviewMessage(role="system", content=system_prompt),
        InterviewMessage(role="assistant", content=ai_first_msg),
    ]
    
    session = InterviewSession(
        session_id=session_id,
        company_id=company_id,
        messages=messages
    )
    
    json_store.write_interview_session(company_id, session_id, session)
    return session


async def send_message(company_id: str, session_id: str, message: str) -> str:
    """Append user message and fetch LLM response for conversation continuation."""
    session = json_store.read_interview_session(company_id, session_id)
    session.messages.append(InterviewMessage(role="user", content=message))
    
    history_str = ""
    for msg in session.messages[1:]: 
        prefix = "Candidate" if msg.role == "user" else "Interviewer"
        history_str += f"{prefix}: {msg.content}\n\n"
        
    user_prompt = f"Transcript:\n{history_str}\n\n[SYSTEM]: As the interviewer, respond naturally to the candidate's last message."
    
    ai_resp = await call_groq(
        system_prompt=session.messages[0].content,
        user_message=user_prompt,
        expect_json=False,
        purpose=f"interview_msg_{session_id}"
    )
    
    session.messages.append(InterviewMessage(role="assistant", content=ai_resp))
    json_store.write_interview_session(company_id, session_id, session)
    return ai_resp


async def get_help(company_id: str, session_id: str) -> dict:
    """Invokes coach logic given current session state without polluting tracking history."""
    session = json_store.read_interview_session(company_id, session_id)
    meta = json_store.read_application_meta(company_id)
    
    last_question = "No question asked yet."
    for msg in reversed(session.messages):
        if msg.role == "assistant":
            last_question = msg.content
            break
            
    prompt_path = settings.BASE_DIR / "backend" / "prompts" / "interview_coach.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_tmpl = f.read()
        
    system_prompt = prompt_tmpl.replace("{current_question}", last_question) \
        .replace("{candidate_profile}", "Zied Cherif - Automation & AI Engineer") \
        .replace("{what_they_look_for}", ", ".join(meta.persona.what_they_look_for)) \
        .replace("{red_flags_to_avoid}", ", ".join(meta.persona.red_flags_to_avoid))
    
    help_json = await call_groq(
        system_prompt=system_prompt,
        user_message="Analyze the question and provide the coaching JSON.",
        expect_json=True,
        purpose=f"interview_help_{session_id}"
    )
    
    return help_json


async def end_session(company_id: str, session_id: str) -> dict:
    """Terminate the simulation and score the transaction against persona filters."""
    session = json_store.read_interview_session(company_id, session_id)
    meta = json_store.read_application_meta(company_id)
    
    prompt_path = settings.BASE_DIR / "backend" / "prompts" / "interview_score.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_tmpl = f.read()
        
    history_str = ""
    for msg in session.messages[1:]:
        prefix = "Candidate" if msg.role == "user" else "Interviewer"
        history_str += f"{prefix}: {msg.content}\n"
        
    system_prompt = prompt_tmpl.replace("{job_title}", meta.company_info.job_title) \
        .replace("{company_name}", meta.company_info.company_name) \
        .replace("{what_they_look_for}", ", ".join(meta.persona.what_they_look_for)) \
        .replace("{red_flags_to_avoid}", ", ".join(meta.persona.red_flags_to_avoid)) \
        .replace("{transcript}", history_str)
    
    score_json = await call_groq(
        system_prompt=system_prompt,
        user_message="Evaluate this transcript and return the JSON score.",
        expect_json=True,
        purpose=f"interview_score_{session_id}"
    )
    
    session.performance_score = float(score_json.get("overall_score", 0.0))
    session.feedback = json.dumps(score_json)
    
    json_store.write_interview_session(company_id, session_id, session)
    return score_json
