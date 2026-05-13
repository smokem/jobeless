import asyncio
from playwright.async_api import async_playwright

async def test_pdf():
    print("Testing Playwright PDF rendering...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content('<h1>Test Playwright PDF</h1><p>If you see this, rendering works.</p>')
            await page.pdf(path='test_pw.pdf', format='A4')
            await browser.close()
            print("SUCCESS: test_pw.pdf generated.")
    except Exception as e:
        print(f"FAILED: Playwright PDF rendering failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_pdf())
