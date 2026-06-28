import httpx
import logging
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

def _fetch_page(url: str) -> str:
    """Fetch a URL and return its HTML as a string. Returns empty on error."""
    try:
        with httpx.Client(timeout=10, follow_redirects=True, headers=HEADERS) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return ""
            return resp.text
    except Exception as e:
        logger.error(f"fetch page error {url}: {e}")
        return ""

def _extract_next_data(html: str) -> dict:
    """Parse the __NEXT_DATA__ JSON from a Vikaspedia page. Returns {} on failure."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return {}
        data_json = script.string or script.text
        return json.loads(data_json)
    except Exception as e:
        logger.error(f"extract __NEXT_DATA__ error: {e}")
        return {}

def _chunk(text: str, max_len: int = 500, max_chunks: int = 5) -> list[str]:
    """Split text into up to max_chunks strings of max_len characters each."""
    words = text.split()
    chunks, current, length = [], [], 0
    for w in words:
        if length + len(w) + 1 > max_len and current:
            chunks.append(" ".join(current))
            if len(chunks) >= max_chunks:
                break
            current, length = [], 0
        current.append(w)
        length += len(w) + 1
    if current and len(chunks) < max_chunks:
        chunks.append(" ".join(current))
    return chunks

def live_retrieve(scheme_name: str, apply_link: str) -> list[str]:
    """Retrieve scheme details.

    1️⃣ Try the official apply_link; if the page contains the scheme name, extract text.
    2️⃣ Otherwise, search Vikaspedia index pages, locate the matching scheme, fetch its detail page via __NEXT_DATA__, and extract text.
    Returns up to five 500‑character chunks, or [] on any failure.
    """
    # Try official link first
    page_html = _fetch_page(apply_link)
    if page_html and scheme_name.lower() in page_html.lower():
        soup = BeautifulSoup(page_html, "html.parser")
        texts = []
        for el in soup.find_all(["p", "li", "h1", "h2", "h3"]):
            txt = el.get_text(strip=True)
            if len(txt) >= 30:
                texts.append(txt)
        combined = " ".join(texts)
        if combined:
            return _chunk(combined)

    # Fallback to Vikaspedia
    search_pages = [
        "https://en.vikaspedia.in/schemesall/state-specific-schemes/welfare-schemes-of-telangana",
        "https://en.vikaspedia.in/schemesall/state-specific-schemes/welfare-schemes-of-andhra-pradesh",
        "https://en.vikaspedia.in/schemesall/central-government-schemes",
    ]
    target = scheme_name.lower()
    for index_url in search_pages:
        html = _fetch_page(index_url)
        if not html:
            continue
        data = _extract_next_data(html)
        items = data.get("props", {}).get("pageProps", {}).get("ssrContentList", [])
        for item in items:
            if item.get("title", "").lower() == target:
                context_path = item.get("context_path")
                if not context_path:
                    continue
                detail_url = f"https://en.vikaspedia.in{context_path}"
                detail_html = _fetch_page(detail_url)
                if not detail_html:
                    continue
                detail_data = _extract_next_data(detail_html)
                content_html = (
                    detail_data.get("props", {})
                    .get("pageProps", {})
                    .get("ssrPageContent", {})
                    .get("content", "")
                )
                if not content_html:
                    continue
                soup = BeautifulSoup(content_html, "html.parser")
                texts = []
                for el in soup.find_all(["p", "li", "h1", "h2", "h3"]):
                    txt = el.get_text(strip=True)
                    if len(txt) >= 30:
                        texts.append(txt)
                combined = " ".join(texts)
                if combined:
                    return _chunk(combined)
                return []
    logger.warning("live_retrieve: scheme %s not found on Vikaspedia", scheme_name)
    return []
