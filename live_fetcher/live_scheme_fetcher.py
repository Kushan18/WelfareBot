import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

async def fetch_scheme_details_live(scheme_name):
    """
    Fetch LIVE details for a specific scheme from government website
    Used when user asks: "What documents do I need for X scheme?"
    """
    
    try:
        # Search on myscheme.gov.in for the scheme
        search_url = f"https://www.myscheme.gov.in/search?q={scheme_name}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(search_url, follow_redirect=True)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get first matching scheme
        first_scheme = soup.find('div', class_='scheme-card')
        
        if not first_scheme:
            logger.warning(f"No scheme found for: {scheme_name}")
            return None
        
        # Extract full scheme page URL
        scheme_link = first_scheme.find('a', class_='scheme-link')
        if not scheme_link:
            return None
        
        scheme_url = scheme_link.get('href')
        if not scheme_url.startswith('http'):
            scheme_url = "https://www.myscheme.gov.in" + scheme_url
        
        # Fetch full scheme page
        detail_response = await client.get(scheme_url, follow_redirect=True)
        detail_response.raise_for_status()
        
        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
        
        # Extract all text content
        full_text = detail_soup.get_text(separator='\n', strip=True)
        
        logger.info(f"Fetched live details for: {scheme_name}")
        
        return {
            "scheme_name": scheme_name,
            "url": scheme_url,
            "content": full_text[:3000]  # First 3000 chars
        }
    
    except Exception as e:
        logger.error(f"Live fetch error for {scheme_name}: {e}")
        return None
