import asyncio
import logging
import random
from pathlib import Path
from typing import Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page

from backend.config import settings
from backend.models.schemas import TargetCompany

logger = logging.getLogger(__name__)

async def human_delay(page: Page = None):
    delay_time = random.uniform(2.0, 5.0)
    await asyncio.sleep(delay_time)
    
async def easy_apply(target: TargetCompany, cv_pdf_path: str) -> dict:
    """Automate LinkedIn Easy Apply."""
    logger.info(f"Starting Playwright Easy Apply for {target.company_name}")
    
    if not settings.LINKEDIN_EMAIL or settings.LINKEDIN_EMAIL == "placeholder@example.com":
        logger.warning("No real LinkedIn credentials. Mocking Easy Apply success.")
        await asyncio.sleep(2)
        return {"success": True, "method": "easy_apply", "timestamp": datetime.now().isoformat(), "error": None}

    user_data_dir = Path(settings.DATA_DIR) / "browser_state"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            # Use persistent context to save cookies/session
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Manual Login Phase - Smart Detection
            logger.info("Checking LinkedIn authentication status...")
            await page.goto("https://www.linkedin.com/feed")
            await page.wait_for_load_state("networkidle")
            
            if "login" in page.url or "checkpoint" in page.url or await page.locator("button.search-global-typeahead__search-button").count() == 0:
                logger.info("MFA or Login required. Waiting 30 seconds for manual interaction...")
                if "login" not in page.url and "checkpoint" not in page.url:
                    await page.goto("https://www.linkedin.com/login")
                
                # Wait for 30 seconds for manual login/MFA
                await asyncio.sleep(30)
                await page.wait_for_load_state("networkidle")
            else:
                logger.info("Already logged in via persistent session. Skipping login wait.")
            
            # Navigate to job
            await page.goto(str(target.job_url))
            await human_delay(page)
            
            # Click Easy Apply
            try:
                # Primary selector
                await page.click("button.jobs-apply-button", timeout=5000)
            except Exception:
                try:
                    # Fallback text
                    await page.click("text=Easy Apply", timeout=5000)
                except Exception as e:
                    logger.error(f"Could not find Easy Apply button: {e}")
                    raise Exception("Easy Apply button not found")
                    
            await human_delay(page)
            
            # Handle multi-step form (simplified stub sequence for resilience)
            max_steps = 10
            for _ in range(max_steps):
                # Try to find file upload
                upload_input = page.locator("input[type='file']")
                if await upload_input.count() > 0:
                    await upload_input.set_input_files(cv_pdf_path)
                    await human_delay()
                    
                # Try Next button
                next_btn = page.locator("button:has-text('Next')")
                if await next_btn.is_visible():
                    await next_btn.click()
                    await human_delay()
                    continue
                    
                # Try Submit button
                submit_btn = page.locator("button:has-text('Submit application')")
                if await submit_btn.is_visible():
                    await submit_btn.click()
                    await human_delay()
                    break
                    
                # Try Review button
                review_btn = page.locator("button:has-text('Review')")
                if await review_btn.is_visible():
                    await review_btn.click()
                    await human_delay()
                    continue
                    
                break # unknown state, let's break
                
            await context.close()
            return {"success": True, "method": "easy_apply", "timestamp": datetime.now().isoformat(), "error": None}

    except Exception as e:
        logger.error(f"Playwright Easy Apply failed: {str(e)}")
        return {"success": False, "method": "easy_apply", "timestamp": datetime.now().isoformat(), "error": str(e)}

async def send_linkedin_dm(hr_linkedin_url: str, message: str) -> dict:
    """Automate LinkedIn DM."""
    logger.info(f"Sending DM to {hr_linkedin_url}")
    
    if not settings.LINKEDIN_EMAIL or settings.LINKEDIN_EMAIL == "placeholder@example.com":
        logger.warning("Mocking LinkedIn DM success.")
        await asyncio.sleep(1)
        return {"success": True, "error": None}

    user_data_dir = Path(settings.DATA_DIR) / "browser_state"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Manual Login Phase - Smart Detection
            await page.goto("https://www.linkedin.com/feed")
            await page.wait_for_load_state("networkidle")
            
            if "login" in page.url or "checkpoint" in page.url:
                logger.info("MFA or Login required. Waiting 30 seconds for manual interaction...")
                if "login" not in page.url and "checkpoint" not in page.url:
                    await page.goto("https://www.linkedin.com/login")
                await asyncio.sleep(30)
                await page.wait_for_load_state("networkidle")
            
            await page.goto(hr_linkedin_url)
            await human_delay()
            
            # Click message
            # Message selectors on LinkedIn vary significantly (e.g. "Message", direct connections, Premium InMail)
            # This is a simplified stub.
            await page.click("button:has-text('Message')")
            await human_delay()
            
            # Type char by char
            editor = page.locator("div[role='textbox']")
            await editor.click()
            for char in message:
                await editor.type(char, delay=random.uniform(20, 100))
                
            await page.click("button:has-text('Send')")
            await human_delay()
            
            await context.close()
            return {"success": True, "error": None}
            
    except Exception as e:
        logger.error(f"DM failed: {str(e)}")
        return {"success": False, "error": str(e)}
