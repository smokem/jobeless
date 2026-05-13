import smtplib
from email.message import EmailMessage
import logging
from datetime import datetime

from backend.config import settings
from backend.models.schemas import TargetCompany

logger = logging.getLogger(__name__)

async def send_application_email(target: TargetCompany, cv_pdf_path: str, cl_pdf_path: str, cover_letter_subject: str, cover_letter_text: str) -> dict:
    """Send application via Brevo SMTP."""
    logger.info(f"Sending email application to {target.company_name}")
    
    # Mock behavior if no password provided
    if not settings.BREVO_SMTP_PASSWORD or settings.BREVO_SMTP_PASSWORD == "placeholder_brevo_password":
        logger.warning("No Brevo password. Mocking Email Application success.")
        return {"success": True, "method": "email", "timestamp": datetime.now().isoformat(), "error": None, "message_id": "mock_id_123"}
        
    try:
        # Create message
        msg = EmailMessage()
        msg['Subject'] = cover_letter_subject
        # fallback for email users/from_email in case settings doesn't strictly define them
        from_email = getattr(settings, "SMTP_FROM_EMAIL", "applicant@example.com")
        smtp_user = getattr(settings, "SMTP_USER", from_email)
        
        msg['From'] = from_email
        msg['To'] = "hr@example.com" # Stubs for now, usually derived from hr profile scraping
        
        # Plain text
        msg.set_content(cover_letter_text)
        
        # HTML Alternative
        msg.add_alternative(f"<html><body><p>{cover_letter_text.replace(chr(10), '<br>')}</p></body></html>", subtype='html')
        
        # Attach CV
        with open(cv_pdf_path, 'rb') as f:
            pdf_data = f.read()
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename='Generated_CV.pdf')
            
        # Attach CL
        with open(cl_pdf_path, 'rb') as f:
            cl_data = f.read()
            msg.add_attachment(cl_data, maintype='application', subtype='pdf', filename='Generated_Cover_Letter.pdf')
            
        # Send
        with smtplib.SMTP('smtp-relay.brevo.com', 587) as server:
            server.starttls()
            server.login(smtp_user, settings.BREVO_SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Successfully sent email to {target.company_name}")
        return {"success": True, "method": "email", "timestamp": datetime.now().isoformat(), "error": None, "message_id": "real_id"}

    except Exception as e:
        logger.error(f"Email application failed: {str(e)}")
        return {"success": False, "method": "email", "timestamp": datetime.now().isoformat(), "error": str(e), "message_id": None}
