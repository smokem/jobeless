# Skill: GAN Scoring

## Purpose
Optimize CV/CL quality through a Generative Adversarial Network (GAN) architecture where a Generator creates content and a Discriminator (HR Persona) evaluates it.

## Key Libraries
- `groq`: For dual-instance inference (Generator vs. Discriminator)
- `python-logging`: For tracking iteration history and scores

## Implementation Pattern
1. **Architecture**:
   - **Generator (Groq Instance B)**: Responsible for drafting the CV/CL based on `profile.json` and the hiring persona.
   - **Discriminator (Groq Instance A)**: Responsible for scoring the output (0–10) from the perspective of the target HR/CEO.
2. **The Loop**:
   - Generator creates Draft v1.
   - Discriminator evaluates Draft v1 and provides specific, critical notes (e.g., "Achievements aren't quantified", "Tone is too casual").
   - If score < 9 and iterations < 5:
     - Notes are fed back to the Generator for regeneration (Draft v{n+1}).
   - If score >= 9 or iterations == 5:
     - Save the best-scoring version as final.
3. **Logging**:
   - Every iteration must be logged in `logs/decisions.log` with the score, discriminator notes, and whether it passed.
4. **Prompting**:
   - Discriminator prompt must include: "You are {HR_NAME} from {COMPANY}. You are looking for {VALUES}. Be extremely critical. If this doesn't wowed you, score it below 7."

## Known Pitfalls
- **Collusion**: LLM instances might start agreeing with each other. Use different system prompts and temperature settings (Generator T=0.7, Discriminator T=0.2) to ensure critical evaluation.
- **Infinite Loops**: Always enforce the `MAX_ITERATIONS = 5` limit in `config.py`.
- **Vanishing Gradients (LLM style)**: If notes are too vague, the generator won't know what to change. Ensure the discriminator prompt asks for "actionable improvements."

## Test Approach
- Verify the loop logic with mock scores.
- Check that `logs/decisions.log` correctly captures iteration data.
- Ensure the loop terminates correctly at the iteration limit.
