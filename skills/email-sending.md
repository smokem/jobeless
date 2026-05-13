# Skill: Email Sending

## Purpose
Send hyper-tailored job applications via email using Brevo SMTP, ensuring high deliverability and professional presentation.

## Key Libraries
- `brevo-python`: For Brevo API/SMTP integration
- `groq`: For generating subject lines and email body text
- `email.mime`: For constructing multi-part emails with attachments

## Implementation Pattern
1. **SMTP Setup**:
   - Use `BREVO_SMTP_PASSWORD` from `.env`.
   - Host: `smtp-relay.brevo.com`, Port: 587.
2. **Content Generation**:
   - **Subject Line**: Use Groq to generate a catchy but professional subject (e.g., "AI Developer Application - Zied Cherif - [Specific Project Reference]").
   - **Body**: Use a plain-text version of the cover letter as the email body. Ensure it references the target company by name and values.
3. **Attachments**:
   - Attach `cv.pdf` and `cover_letter.pdf` from `applications/{company_id}/`.
   - Ensure file names are professional: `Zied_Cherif_CV.pdf`.
4. **Deliverability**:
   - Always include a `text/plain` alternative to the `text/html` body.
   - Include a professional signature with LinkedIn and Portfolio links.
   - Limit to 300 emails per day as per Brevo free tier.

## Known Pitfalls
- **Spam Filters**: Avoid "urgent" or "money" related keywords in subject lines. Always use a verified sender email address.
- **Attachment Size**: Ensure PDFs are optimized (< 2MB) to avoid rejection by corporate mail servers.
- **Rate Limits**: If the limit (300/day) is hit, the application queue must pause and resume the next day.

## Test Approach
- Send a test email to a personal "trap" address.
- Verify that both PDF attachments are readable and correctly named.
- Check the spam score of generated emails using a tool like Mail-Tester.
