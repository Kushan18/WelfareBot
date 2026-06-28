from groq import Groq
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def structure_scheme_with_groq(groq_client: Groq, raw_scheme: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Takes raw scraped scheme data and structures it with Groq
    Returns clean JSON with extracted fields
    """
    
    prompt = f"""
    Parse this government scheme information and extract structured data.
    
    Raw data:
    Name: {raw_scheme.get('name')}
    Ministry: {raw_scheme.get('ministry')}
    Description: {raw_scheme.get('description')}
    URL: {raw_scheme.get('url')}
    
    Extract and structure as JSON with these fields:
    {{
        "name": "Scheme name",
        "ministry": "Ministry name",
        "description": "1-2 sentence description",
        "eligibility": "Who is eligible (SC/ST/OBC/General/Women/Youth/Farmers/Students)",
        "benefits": "What you get (amount, support, etc)",
        "documents_needed": ["List", "of", "documents"],
        "apply_link": "{raw_scheme.get('url')}",
        "deadline": "Application deadline (if available, else 'Ongoing')",
        "eligibility_rules": {{
            "state": "all",
            "caste_category": "all",
            "occupation": "all",
            "gender": "all",
            "min_age": 0,
            "max_age": 100,
            "max_income": 10000000
        }}
    }}
    
    Return ONLY valid JSON, nothing else.
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a JSON extraction engine. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            timeout=15
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        structured = json.loads(response_text)
        logger.info(f"Structured scheme: {structured.get('name')}")
        return structured
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"Groq structuring error: {e}")
        return None
