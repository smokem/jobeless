import logging
import asyncio
import urllib.parse
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from backend.config import settings
from backend.models.schemas import TargetCompany

logger = logging.getLogger(__name__)

_GUEST_JOBS_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.linkedin.com/jobs/",
    "X-Requested-With": "XMLHttpRequest",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def scrape_linkedin_jobs(role: str, location: str, radius_km: int = 25) -> List[TargetCompany]:
    """
    Scrape LinkedIn job listings.
    Strategy: HTTP guest API (no auth) → Playwright fallback → raise on both failing.
    Never returns mock/fake data.
    """
    logger.info(f"Scraping LinkedIn: '{role}' in '{location}' ({radius_km} km)")

    # 1. HTTP guest API — fastest, no auth needed
    try:
        raw = await _scrape_jobs_http(role, location)
        if raw:
            targets = _map_to_targets(raw, role, location)
            logger.info(f"HTTP scrape succeeded: {len(targets)} jobs.")
            await _log_debug("linkedin_scraper", "scrape_linkedin_jobs",
                             {"role": role, "location": location}, outcome="success (http)")
            return targets
        logger.warning("HTTP guest API returned 0 results, trying Playwright...")
    except Exception as exc:
        logger.warning(f"HTTP scrape failed ({exc}), trying Playwright...")
        await _log_debug("linkedin_scraper", "scrape_linkedin_jobs",
                         {"role": role, "location": location},
                         error=str(exc), outcome="http_failed")

    # 2. Playwright fallback — can handle JS-heavy pages and login
    try:
        raw = await _scrape_jobs_playwright(role, location, radius_km)
        if raw:
            targets = _map_to_targets(raw, role, location)
            logger.info(f"Playwright scrape succeeded: {len(targets)} jobs.")
            await _log_debug("linkedin_scraper", "scrape_linkedin_jobs",
                             {"role": role, "location": location}, outcome="success (playwright)")
            return targets
    except Exception as exc:
        logger.error(f"Playwright scrape failed ({exc})")
        await _log_debug("linkedin_scraper", "scrape_linkedin_jobs",
                         {"role": role, "location": location},
                         error=str(exc), outcome="playwright_failed")

    raise RuntimeError(
        "Could not fetch jobs from LinkedIn. LinkedIn may be rate-limiting requests. "
        "Try again in a few minutes, or add jobs manually using the 'Add Manually' button."
    )


async def scrape_company_profile(linkedin_url: str) -> dict:
    """Scrape a LinkedIn company About page. Returns empty dict on failure."""
    if not linkedin_url:
        return {}
    try:
        return await _scrape_company_playwright(linkedin_url)
    except Exception as exc:
        logger.warning(f"Company profile scrape failed ({exc}).")
    return {}


async def scrape_person_posts(linkedin_url: str, max_posts: int = 20) -> List[str]:
    """Scrape recent LinkedIn posts for a person. Returns empty list on failure."""
    if not linkedin_url:
        return []
    try:
        return await _scrape_posts_playwright(linkedin_url, max_posts)
    except Exception as exc:
        logger.warning(f"Person posts scrape failed ({exc}).")
    return []


# ---------------------------------------------------------------------------
# HTTP guest API scraper (primary — no auth required)
# ---------------------------------------------------------------------------

async def _scrape_jobs_http(role: str, location: str) -> List[dict]:
    """Fetch jobs via LinkedIn's public guest API."""
    import httpx
    from bs4 import BeautifulSoup

    params = {"keywords": role, "location": location, "start": "0", "pageSize": "25"}

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(_GUEST_JOBS_API, params=params, headers=_HEADERS)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs: List[dict] = []

    for card in soup.find_all("li"):
        title_el    = card.find("h3", class_="base-search-card__title")
        company_el  = card.find("h4", class_="base-search-card__subtitle")
        loc_el      = card.find("span", class_="job-search-card__location")
        link_el     = card.find("a", class_="base-card__full-link") or \
                      card.find("a", href=lambda h: h and "/jobs/view/" in str(h))
        co_link_el  = card.find("a", href=lambda h: h and "/company/" in str(h))
        ea_el       = card.find(class_="job-search-card__easy-apply-label")

        if not link_el:
            continue
        raw_href = link_el.get("href") or ""
        # Keep only the clean job URL (strip tracking params)
        job_url = raw_href.split("?")[0]
        if "/jobs/view/" not in job_url:
            continue

        co_href = (co_link_el.get("href") or "").split("?")[0] if co_link_el else ""

        jobs.append({
            "title":      title_el.get_text(strip=True) if title_el else "",
            "company":    company_el.get_text(strip=True) if company_el else "Unknown",
            "companyUrl": co_href,
            "jobUrl":     job_url,
            "location":   loc_el.get_text(strip=True) if loc_el else location,
            "easyApply":  bool(ea_el),
        })

    return jobs


# ---------------------------------------------------------------------------
# Playwright scraper (fallback — handles JS + auth)
# ---------------------------------------------------------------------------

async def _new_browser_context(pw):
    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox",
              "--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        user_agent=_USER_AGENT,
        viewport={"width": 1366, "height": 768},
        locale="en-US",
    )
    return browser, context


async def _login(page) -> bool:
    email = settings.LINKEDIN_EMAIL
    password = settings.LINKEDIN_PASSWORD
    if not email or not password:
        return False
    try:
        await page.goto("https://www.linkedin.com/login",
                        wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(1.0)
        await page.fill("#username", email)
        await page.fill("#password", password)
        await asyncio.sleep(0.4)
        await page.click("button[type='submit']")
        await asyncio.sleep(3)
        url = page.url
        return "login" not in url and "checkpoint" not in url and "authwall" not in url
    except Exception as exc:
        logger.warning(f"LinkedIn login attempt failed: {exc}")
        return False


async def _scrape_jobs_playwright(role: str, location: str, radius_km: int) -> List[dict]:
    from playwright.async_api import async_playwright

    kw = urllib.parse.quote_plus(role)
    loc = urllib.parse.quote_plus(location)
    search_url = (
        f"{_LINKEDIN_JOBS_URL}?keywords={kw}&location={loc}"
        f"&distance={radius_km}&f_TPR=r604800&f_JT=F%2CC"
    )

    async with async_playwright() as pw:
        browser, context = await _new_browser_context(pw)
        page = await context.new_page()
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            if "login" in page.url or "authwall" in page.url:
                logger.info("LinkedIn auth wall hit — attempting login...")
                ok = await _login(page)
                if ok:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)

            for _ in range(4):
                await page.keyboard.press("End")
                await asyncio.sleep(0.7)

            return await _extract_job_cards(page)
        finally:
            await browser.close()


async def _extract_job_cards(page) -> List[dict]:
    return await page.evaluate("""
        () => {
            const results = [];

            let cards = Array.from(document.querySelectorAll(
                '.jobs-search__results-list li, .job-search-card, .base-card'
            ));
            if (!cards.length) {
                cards = Array.from(document.querySelectorAll(
                    '.jobs-search-results__list-item, .scaffold-layout__list-item'
                ));
            }

            cards.forEach(card => {
                const titleEl = card.querySelector(
                    'h3.base-search-card__title a, h3.base-search-card__title, ' +
                    '.job-card-list__title, .job-card-container__link, h3 a[href*="/jobs/view/"]'
                );
                const linkEl = card.querySelector(
                    'a.base-card__full-link, a[href*="/jobs/view/"], .job-card-list__title--link'
                );
                const companyEl = card.querySelector(
                    'h4.base-search-card__subtitle a, h4.base-search-card__subtitle, ' +
                    '.job-card-container__company-name, .artdeco-entity-lockup__subtitle'
                );
                const companyLinkEl = card.querySelector(
                    'h4.base-search-card__subtitle a, a[href*="/company/"]'
                );
                const locationEl = card.querySelector(
                    '.job-search-card__location, .job-card-container__metadata-item'
                );
                const easyApplyEl = card.querySelector(
                    '.job-search-card__easy-apply-label, [aria-label*="Easy Apply"]'
                );

                let jobUrl = linkEl ? (linkEl.href || linkEl.getAttribute('href') || '') : '';
                if (!jobUrl) return;
                if (!jobUrl.startsWith('http')) jobUrl = 'https://www.linkedin.com' + jobUrl;
                jobUrl = jobUrl.split('?')[0];
                if (!jobUrl.includes('/jobs/view/')) return;

                let companyUrl = companyLinkEl
                    ? (companyLinkEl.href || companyLinkEl.getAttribute('href') || '')
                    : '';
                if (companyUrl && !companyUrl.startsWith('http')) {
                    companyUrl = 'https://www.linkedin.com' + companyUrl;
                }
                companyUrl = companyUrl.split('?')[0];

                results.push({
                    title:      titleEl   ? titleEl.textContent.trim()   : '',
                    company:    companyEl ? companyEl.textContent.trim()  : 'Unknown',
                    companyUrl: companyUrl,
                    location:   locationEl ? locationEl.textContent.trim() : '',
                    jobUrl:     jobUrl,
                    easyApply:  !!(easyApplyEl || card.textContent.includes('Easy Apply')),
                });
            });

            const seen = new Set();
            return results.filter(j => {
                if (seen.has(j.jobUrl)) return false;
                seen.add(j.jobUrl);
                return true;
            });
        }
    """)


async def _scrape_company_playwright(url: str) -> dict:
    from playwright.async_api import async_playwright

    about_url = url.rstrip("/") + "/about/"
    async with async_playwright() as pw:
        browser, context = await _new_browser_context(pw)
        page = await context.new_page()
        try:
            await page.goto(about_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1.5)
            if "login" in page.url or "authwall" in page.url:
                await _login(page)
                await page.goto(about_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(1.5)

            return await page.evaluate("""
                () => ({
                    about: document.querySelector(
                        '.org-about-us-organization-description__text, ' +
                        '.core-section-container__content p'
                    )?.textContent?.trim() || '',
                    size: document.querySelector(
                        '[data-test-id="about-us__size"] dd, ' +
                        '.org-about-company-module__company-size-definition-text'
                    )?.textContent?.trim() || '',
                    industry: document.querySelector(
                        '[data-test-id="about-us__industry"] dd, ' +
                        '.org-about-company-module__industry'
                    )?.textContent?.trim() || '',
                })
            """)
        finally:
            await browser.close()


async def _scrape_posts_playwright(url: str, max_posts: int) -> List[str]:
    from playwright.async_api import async_playwright

    recent_url = url.rstrip("/") + "/recent-activity/shares/"
    async with async_playwright() as pw:
        browser, context = await _new_browser_context(pw)
        page = await context.new_page()
        try:
            await page.goto(recent_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1.5)
            if "login" in page.url or "authwall" in page.url:
                await _login(page)
                await page.goto(recent_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(1.5)

            return await page.evaluate("""
                (maxPosts) => {
                    const els = Array.from(document.querySelectorAll(
                        '.feed-shared-update-v2__description, .attributed-text-segment-list__content'
                    ));
                    return els.slice(0, maxPosts)
                               .map(el => el.textContent.trim())
                               .filter(t => t.length > 20);
                }
            """, max_posts)
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------

def _map_to_targets(raw: List[dict], role: str, location: str) -> List[TargetCompany]:
    targets = []
    for idx, job in enumerate(raw[:50]):
        job_url = job.get("jobUrl", "")
        company_url = job.get("companyUrl") or ""
        if not job_url:
            continue
        if company_url and not company_url.startswith("http"):
            company_url = "https://www.linkedin.com" + company_url
        if not company_url:
            company_url = "https://www.linkedin.com/company/unknown"
        try:
            targets.append(TargetCompany(
                company_id=f"tgt_{int(datetime.now().timestamp() * 1000)}_{idx}",
                company_name=job.get("company", "Unknown Company"),
                company_linkedin=company_url,
                job_title=job.get("title") or role,
                job_url=job_url,
                apply_type="easy_apply" if job.get("easyApply") else "external",
                location=job.get("location") or location,
                status="pending",
            ))
        except Exception as exc:
            logger.debug(f"Skipping job entry: {exc}")
    return targets


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

async def _log_debug(
    module: str, function: str, params: dict,
    outcome: str, error: Optional[str] = None
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_type = "ERROR" if error else "INFO"
    param_str = " ".join(f"{k}={v}" for k, v in params.items())
    entry = f"[{timestamp}] [{log_type}] module={module} function={function}\n  {param_str}\n"
    if error:
        entry += f"  error={error}\n"
    entry += f"  outcome={outcome}\n"
    try:
        log_path = Path(settings.DEBUG_LOG)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as exc:
        logger.error(f"Could not write debug.log: {exc}")
