import asyncio
from scraper.groq_structurer import structure_scheme_with_groq
from groq import Groq
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

async def run_scraper():
    print('Adding known schemes from AP, Telangana, and India...')
    
    # Initialize Groq client
    groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    
    # Known schemes from AP, Telangana, and India
    known_schemes = [
        {
            "name": "Rythu Bharosa",
            "ministry": "Andhra Pradesh Government",
            "description": "Financial assistance of Rs 13,500 per year to farmers in Andhra Pradesh",
            "url": "https://ap.gov.in/rythu-bharosa",
            "state": "Andhra Pradesh"
        },
        {
            "name": "Telangana Rythu Bandhu",
            "ministry": "Telangana Government",
            "description": "Financial assistance of Rs 10,000 per acre to farmers in Telangana",
            "url": "https://telangana.gov.in/rythu-bandhu",
            "state": "Telangana"
        },
        {
            "name": "PM Kisan Samman Nidhi",
            "ministry": "Government of India",
            "description": "Direct income support of Rs 6,000 per year to farmers across India",
            "url": "https://pmkisan.gov.in",
            "state": "all"
        },
        {
            "name": "Aarogyasri Health Card",
            "ministry": "Telangana Government",
            "description": "Health insurance covering up to Rs 10 lakh for Telangana residents",
            "url": "https://telangana.gov.in/aarogyasri",
            "state": "Telangana"
        },
        {
            "name": "YSR Aasara Pension",
            "ministry": "Andhra Pradesh Government",
            "description": "Monthly pension of Rs 2,750 to elderly, widows, and disabled in AP",
            "url": "https://ap.gov.in/aasara",
            "state": "Andhra Pradesh"
        },
        {
            "name": "PM Awas Yojana",
            "ministry": "Government of India",
            "description": "Housing for All scheme providing financial assistance for building houses",
            "url": "https://pmay.gov.in",
            "state": "all"
        },
        {
            "name": "Telangana Kalyana Lakshmi",
            "ministry": "Telangana Government",
            "description": "Financial assistance of Rs 1,00,116 for marriage of girls from SC/ST families",
            "url": "https://telangana.gov.in/kalyana-lakshmi",
            "state": "Telangana"
        },
        {
            "name": "Amma Vodi",
            "ministry": "Andhra Pradesh Government",
            "description": "Financial assistance of Rs 15,000 per year for education of children from poor families",
            "url": "https://ap.gov.in/amma-vodi",
            "state": "Andhra Pradesh"
        }
    ]
    
    # Structure with Groq
    structured = []
    for scheme in known_schemes:
        print(f'\nProcessing: {scheme.get("name", "Unknown")}')
        structured_scheme = structure_scheme_with_groq(groq_client, scheme)
        if structured_scheme:
            structured.append(structured_scheme)
            print(f'Structured: {structured_scheme.get("name", "Unknown")}')
        else:
            print('Failed to structure')
    
    # Save to staging
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['welfarebot']
    staging = db['staging']
    
    if structured:
        staging.delete_many({})
        staging.insert_many(structured)
        print(f'\nSaved {len(structured)} schemes to staging collection')
    else:
        print('\nNo structured schemes to save')

if __name__ == '__main__':
    asyncio.run(run_scraper())
