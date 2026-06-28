import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import httpx

logger = logging.getLogger(__name__)

async def fetch_schemes_from_myscheme() -> List[Dict[str, Any]]:
    """
    Fetch schemes from myscheme.gov.in API using Playwright
    Returns list of raw scheme data
    """
    try:
        url = "https://www.myscheme.gov.in/search"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Intercept network requests to find API
            api_data = []
            
            def handle_response(response):
                if "api" in response.url.lower() or "schemes" in response.url.lower():
                    try:
                        if response.status == 200:
                            api_data.append({
                                "url": response.url,
                                "status": response.status
                            })
                    except:
                        pass
            
            page.on("response", handle_response)
            
            # Navigate to the page
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for dynamic content
            await page.wait_for_timeout(5000)
            
            logger.info(f"API calls detected: {len(api_data)}")
            for api in api_data:
                logger.info(f"  - {api['url']}")
            
            # Try to extract from page content
            schemes = []
            
            # Look for JSON data in script tags
            scripts = await page.query_selector_all('script')
            for script in scripts:
                content = await script.inner_text()
                if 'scheme' in content.lower() and len(content) > 100:
                    try:
                        import json
                        # Try to extract JSON from script content
                        if '{' in content and '}' in content:
                            # Find JSON-like structures
                            start = content.find('{')
                            end = content.rfind('}') + 1
                            json_str = content[start:end]
                            try:
                                data = json.loads(json_str)
                                logger.info(f"Found JSON data in script")
                            except:
                                pass
                    except:
                        pass
            
            # Fallback: Try direct HTTP to known API endpoints
            api_endpoints = [
                "https://api.myscheme.gov.in/schemes",
                "https://www.myscheme.gov.in/api/schemes",
                "https://myscheme.gov.in/api/schemes"
            ]
            
            for api_url in api_endpoints:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.get(api_url)
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                logger.info(f"Successfully fetched from API: {api_url}")
                                for item in data[:10]:
                                    schemes.append({
                                        "name": item.get("name", "Unknown"),
                                        "description": item.get("description", ""),
                                        "url": item.get("url", ""),
                                        "ministry": item.get("ministry", ""),
                                        "raw_data": item
                                    })
                                break
                except Exception as e:
                    logger.warning(f"API {api_url} failed: {e}")
                    continue
            
            await browser.close()
            
            logger.info(f"Total schemes scraped: {len(schemes)}")
            return schemes
    
    except Exception as e:
        logger.error(f"Fetch schemes error: {e}")
        return []

async def fetch_schemes_from_alternative_sources() -> List[Dict[str, Any]]:
    """
    Fetch schemes from alternative government sources
    Focus on AP, Telangana, and India schemes
    """
    schemes = []
    
    # Known government scheme portals
    sources = [
        {
            "name": "Telangana Schemes",
            "url": "https://telangana.gov.in/schemes",
            "state": "Telangana"
        },
        {
            "name": "AP Schemes",
            "url": "https://www.ap.gov.in/schemes",
            "state": "Andhra Pradesh"
        },
        {
            "name": "India Gov Schemes",
            "url": "https://www.india.gov.in/schemes",
            "state": "all"
        }
    ]
    
    for source in sources:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(source["url"])
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for scheme links
                    links = soup.find_all('a')
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text().strip()
                        
                        # Filter for scheme-related links
                        if any(kw in text.lower() for kw in ['scheme', 'yojana', 'program', 'kalyana', 'pension', 'scholarship']):
                            if text and len(text) > 5:
                                schemes.append({
                                    "name": text,
                                    "description": f"Government scheme from {source['name']}",
                                    "url": href if href.startswith('http') else source['url'] + href,
                                    "state": source['state'],
                                    "source": source['name']
                                })
                    
                    logger.info(f"Found {len([s for s in schemes if s['source'] == source['name']])} schemes from {source['name']}")
                    
                    if len(schemes) >= 10:
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to fetch from {source['name']}: {e}")
            continue
    
    return schemes[:20]  # Limit to 20 schemes
