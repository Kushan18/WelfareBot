import os
import logging
import httpx
from scraper.base import make_scheme

logger = logging.getLogger(__name__)

# Common headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://api.myscheme.gov.in/",
    "Origin": "https://api.myscheme.gov.in",
    "X-Requested-With": "XMLHttpRequest",
}

# Include optional API key from environment variable
api_key = os.getenv("MYSCHEME_API_KEY")
if api_key:
    HEADERS["Authorization"] = f"Bearer {api_key}"
    logger.info("myscheme: using API key from environment variable")

def _fetch_state_schemes(state_name: str, state_param: str) -> list:
    """Fetch schemes for a given state using the public myscheme JSON API.
    Returns a list of normalized scheme dictionaries.
    """
    url = (
        "https://api.myscheme.gov.in/schemes/v4/search?lang=en&q=&sort=&from=0&size=50&state="
        + state_param
    )
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 403:
            logger.warning(f"myscheme {state_name}: received 403 Forbidden, possible blocking. Returning empty list.")
            return []
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"myscheme {state_name}: API response keys {list(data.keys())}")
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
        schemes = []
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
        logger.info(f"myscheme {state_name}: fetched {len(schemes)} schemes via API")
        return schemes
    except Exception as e:
        logger.error(f"myscheme {state_name} failed: {e}")
        return []

def scrape() -> list:
    """Run scraping for Telangana and Andhra Pradesh via the JSON API.
    Returns a combined list of schemes.
    """
    all_schemes = []
    all_schemes += _fetch_state_schemes("Telangana", "Telangana")
    all_schemes += _fetch_state_schemes("Andhra Pradesh", "Andhra%20Pradesh")
    logger.info(f"myscheme: scraped total {len(all_schemes)} schemes")
    return all_schemes