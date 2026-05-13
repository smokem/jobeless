# Skill: Company Research

## Purpose
Automate the discovery and deep analysis of target companies and their decision-makers to build hyper-accurate hiring personas.

## Key Libraries
- `apify-client`: For LinkedIn scraper actor integration
- `groq`: For persona synthesis from raw social data
- `pydantic`: For persona schema validation

## Implementation Pattern
1. **Actor Selection**: Use Apify actors:
   - `apify/linkedin-jobs-scraper` for initial discovery.
   - `apify/linkedin-profile-scraper` for HR/CEO profiles.
   - `apify/website-content-crawler` for company values/culture.
2. **Data Extraction**:
   - Scrape company website "About" and "Careers" pages.
   - Extract last 20 LinkedIn posts from the CEO and HR Lead.
   - Identify recurring themes in social media communication (e.g., "growth mindset", "technical excellence").
3. **Synthesis via Groq**:
   - Input: Scraped raw JSON data.
   - System Prompt: "Analyze the following social data and identify the core values, communication style, and preferences of this hiring team."
   - Output: Validated JSON persona matching the schema in PRD.md.
4. **Storage**:
   - Save the final persona to `applications/{company_id}/meta.json`.

## Known Pitfalls
- **Empty Profiles**: If HR/CEO has no public posts, fallback to company-wide mission statements.
- **Privacy Blocks**: Scrapers may fail due to LinkedIn's anti-bot measures. Ensure the Apify actor uses high-quality proxy rotation.
- **Outdated Info**: A CEO's posts from 3 years ago might not reflect current culture. Bias the analysis towards recent activity (last 6 months).

## Test Approach
- Validate persona synthesis with mock scraper data.
- Verify that `meta.json` is created in the correct company folder.
- Ensure all mandatory fields in the persona schema are populated.
