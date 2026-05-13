# Skill: Playwright Automation

## Purpose
Automate job application submissions, specifically LinkedIn Easy Apply, while maintaining account safety and appearing human-like.

## Key Libraries
- `playwright`: For browser automation
- `python-dotenv`: For managing LinkedIn credentials

## Implementation Pattern
1. **Easy Apply Flow**:
   - **Login**: Navigate to `linkedin.com/login` and use `LINKEDIN_EMAIL`/`LINKEDIN_PASSWORD`.
   - **Job Navigation**: Navigate directly to the `job_url` from `targets.json`.
   - **Form Submission**:
     - Click "Easy Apply" button.
     - Detect and fill all form fields (Phone, Email, Experience level).
     - Upload the generated `cv.pdf`.
     - Handle multi-step forms (Next -> Next -> Submit).
2. **Human-like Behavior**:
   - **Delays**: Use `random.uniform(2, 8)` seconds between clicks.
   - **Scrolling**: Scroll to the bottom of the job description before clicking "Apply."
   - **Movement**: Use `page.mouse.move()` to simulate non-linear cursor paths (optional but recommended).
3. **Safety & Rate Limiting**:
   - **Daily Limit**: Hard cap at 20 applications per day as per `config.py`.
   - **Retries**: Attempt 3 different selector strategies if a button isn't found before marking as "failed."
   - **State Persistence**: Store browser context/cookies to avoid repeated logins.
4. **Selector Strategy**:
   - Primary: Data-test attributes or specific IDs.
   - Fallback: ARIA labels or text content (e.g., `text="Easy Apply"`).

## Known Pitfalls
- **Selector Changes**: LinkedIn frequently updates its DOM. Use flexible CSS or XPath and log failures in `logs/debug.log` for manual review.
- **Account Flagging**: Sudden bursts of activity trigger "Suspicious login." Always run on the user's local IP (don't use data center proxies for login).
- **Infinite Modals**: Some "Easy Apply" flows have unexpected questions. If a field is unknown, log the DOM and skip the application.

## Test Approach
- Run Playwright in `headless=False` mode during development to verify flow visually.
- Mock the submission API to test the state machine without actually applying.
- Verify rate limit enforcement by attempting 21 applications in a test loop.
