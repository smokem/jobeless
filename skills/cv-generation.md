# Skill: CV Generation

## Purpose
Generate hyper-tailored CVs by mapping a user's master profile to a target company's hiring persona, followed by high-fidelity PDF rendering.

## Key Libraries
- `groq`: For Llama 3.3 70b JSON generation
- `playwright`: For robust HTML/CSS to PDF conversion (Chromium-based)
- `pydantic`: For CV schema validation

## Implementation Pattern
1. **Prompting**: Use Llama 3.3 70b with a system prompt that enforces strict adherence to the target persona's tone and values.
2. **Structure**: Force the CV JSON to follow a hierarchy:
   - Education (Top)
   - Work Experience (Quantified achievements)
   - Projects (Relevant to the role)
   - Skills (Filtered/Ranked)
   - Soft Skills (Bottom)
3. **1-Page Constraint**: Use narrow margins and optimized font sizes (10-11pt body) in the CSS template to ensure content fits on one page.
4. **ATS Keywords**: Inject keywords found in the company's job description and persona synthesis into the experience bullet points.
5. **Rendering**:
   - Generate HTML from CV JSON using a Jinja2 template.
   - Convert HTML to PDF using `playwright` (Chromium PDF rendering).

## Known Pitfalls
- **Hallucinations**: LLM might invent dates or technologies not in `profile.json`. Use strict few-shot prompting to prevent this.
- **Over-tailoring**: Making bullet points sound unbelievable. Enforce a "fact-checking" step against the source profile.
- **PDF Overflow**: Content exceeding one page. Implement a "character count" check on bullet points before rendering.
- **Dependency Issues**: WeasyPrint requires GTK+ on Windows. Playwright resolves this by bundling its own Chromium binaries.

## Test Approach
- Validate CV JSON against Pydantic schema.
- Mock Groq response with valid/invalid data to test error handling.
- Verify PDF page count is exactly 1.
