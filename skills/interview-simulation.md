# Skill: Interview Simulation

## Purpose
Prepare the user for real interviews by simulating a live chat session with a hiring persona built from target company research.

## Key Libraries
- `groq`: For persona-based chat and performance scoring
- `react`: For the frontend chat interface

## Implementation Pattern
1. **Persona Injection**:
   - Load `meta.json` from `applications/{company_id}/`.
   - Build a System Prompt: "You are {HR_NAME} from {COMPANY}. You are interviewing Zied Cherif for the {JOB_TITLE} position. Your tone is {TONE}. Focus on {WHAT_THEY_LOOK_FOR} and watch out for {RED_FLAGS}."
2. **Session Management**:
   - Start the session by having the AI introduce itself and ask the first question.
   - Maintain the `messages` array in the session JSON.
3. **"Help Me" Button**:
   - When clicked, send the current exchange to a separate Groq instance.
   - Request: "Analyze this interview moment. What is the hidden intent behind the interviewer's question? Provide an ideal answer structure for Zied."
   - Display the response in a sidebar/overlay.
4. **Scoring**:
   - End the session after 10–15 messages or manual "End" click.
   - Groq evaluates the full transcript against the persona's values.
   - Output: Score (0–10) and feedback on specific answers.
5. **Storage**:
   - save to `data/interview_sessions/{company_id}/{session_id}.json`.

## Known Pitfalls
- **Looping**: LLM might repeat the same question. Monitor conversation history and prompt the AI to move to a new topic if repetition is detected.
- **Out of Character**: The AI might become too "assistant-like." Strict system prompting is required to maintain the interviewer's "gatekeeper" persona.
- **Vague Feedback**: Discriminator must be coached to provide critical, non-generic feedback (e.g., "Answer was too technical for this HR-focused interview").

## Test Approach
- Simulate a full interview session with mock user inputs.
- Verify that the "Help Me" button returns relevant context-aware coaching.
- Ensure only one active session per company is running at a time.
