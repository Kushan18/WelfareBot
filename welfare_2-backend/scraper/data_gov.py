import httpx
from scraper.base import make_scheme
import logging

logger = logging.getLogger(__name__)
BASE = "https://data.gov.in/api/datastore/resource.json"
RESOURCE_ID = "6176b896-d8c2-4426-b3db-4cf6bf585e16"

def scrape():
    schemes = []
    offset = 0
    while True:
        try:
            url = f"{BASE}?resource_id={RESOURCE_ID}&limit=100&offset={offset}"
            resp = httpx.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                break
            data = resp.json()
            records = data.get("records") or []
            if not records:
                break
            for r in records:
                schemes.append(make_scheme({
                    "name": str(r.get("scheme_name") or r.get("title") or ""),
                    "description": str(r.get("description") or ""),
                    "eligibility": str(r.get("eligibility") or ""),
                    "benefits": str(r.get("benefits") or ""),
                    "apply_link": str(r.get("url") or r.get("apply_link") or "https://data.gov.in"),
                    "state": str(r.get("state") or "Central"),
                    "source": "data.gov.in",
                    "category": str(r.get("category") or "General"),
                }))
            offset += 100
            if len(records) < 100:
                break
        except Exception as e:
            logger.error(f"data_gov offset {offset} failed: {e}")
            break
    logger.info(f"data_gov: scraped {len(schemes)} schemes")
    return schemes
