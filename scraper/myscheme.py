import os
import logging
import asyncio
from playwright.async_api import async_playwright
from scraper.base import make_scheme

logger = logging.getLogger(__name__)

async def _fetch_state_schemes_playwright(state_name: str, state_param: str) -> list:
    """Fetch schemes for a given state using Playwright to render JavaScript.
    Returns a list of normalized scheme dictionaries.
    """
    url = (
        "https://api.myscheme.gov.in/schemes/v4/search?lang=en&q=&sort=&from=0&size=50&state="
        + state_param
    )
    schemes = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set headers to mimic real browser
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept": "application/json, text/plain, */*",
            })
            
            # Navigate to the API endpoint
            response = await page.goto(url, wait_until="networkidle", timeout=30000)
            
            if response.status == 403:
                logger.warning(f"myscheme {state_name}: received 403 Forbidden via Playwright. Returning empty list.")
                await browser.close()
                return []
            
            # Get the response body
            content = await page.content()
            
            # Try to extract JSON from the page
            try:
                # If it's a direct API response, get the text
                text = await response.text()
                import json
                data = json.loads(text)
            except:
                # If it's an HTML page, try to find JSON in script tags
                text = await page.evaluate("() => document.body.innerText")
                import json
                data = json.loads(text)
            
            await browser.close()
            
            logger.info(f"myscheme {state_name}: Playwright response keys {list(data.keys())}")
            
            # Locate scheme list
            schemes_raw = (
                data.get("data", {}).get("schemes")
                or data.get("hits", {}).get("hits")
                or data.get("schemes")
                or []
            )
            
            if not isinstance(schemes_raw, list):
                logger.warning(f"myscheme {state_name}: unexpected format, returning []")
                return []
            
            for rec in schemes_raw:
                try:
                    scheme = make_scheme({
                        "name": rec.get("name") or rec.get("title") or "",
                        "description": rec.get("description") or rec.get("details") or "",
                        "eligibility": rec.get("eligibility") or "",
                        "benefits": rec.get("benefits") or "",
                        "apply_link": rec.get("apply_link") or rec.get("url") or "",
                        "state": state_name,
                        "source": "myscheme.gov.in",
                        "category": rec.get("category") or "General",
                    })
                    schemes.append(scheme)
                except Exception as e:
                    logger.error(f"myscheme {state_name}: record error {e}")
            
            logger.info(f"myscheme {state_name}: fetched {len(schemes)} schemes via Playwright")
            return schemes
            
    except Exception as e:
        logger.error(f"myscheme {state_name} Playwright failed: {e}")
        return []

def scrape() -> list:
    """Run scraping for Telangana and Andhra Pradesh using Playwright.
    Returns a combined list of schemes.
    """
    all_schemes = []
    
    # Run async Playwright scraping
    async def run_all():
        results = await asyncio.gather(
            _fetch_state_schemes_playwright("Telangana", "Telangana"),
            _fetch_state_schemes_playwright("Andhra Pradesh", "Andhra%20Pradesh"),
            return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"myscheme: scraping error {result}")
            elif isinstance(result, list):
                all_schemes.extend(result)
    
    asyncio.run(run_all())
    
    logger.info(f"myscheme: scraped total {len(all_schemes)} schemes")
    return all_schemes