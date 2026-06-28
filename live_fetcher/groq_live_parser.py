from groq import Groq
import logging

logger = logging.getLogger(__name__)

def answer_scheme_question_with_live_data(groq_client, scheme_name, user_question, live_data):
    """
    Use Groq to answer user's question based on LIVE fetched scheme data
    No hallucination - answer must be from live_data
    """
    
    if not live_data:
        return f"I couldn't fetch live details for {scheme_name}. Try checking myscheme.gov.in directly."
    
    prompt = f"""
    User asked about {scheme_name}: "{user_question}"
    
    Here's the LIVE official data from government website:
    {live_data['content']}
    
    Answer the user's question based ONLY on this official data.
    If the answer is not in the data, say "This information is not in the official guidelines."
    Keep answer to 2-3 sentences.
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are answering based on OFFICIAL government scheme data. Never guess or hallucinate. If information is not in the provided data, say so clearly."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            timeout=15
        )
        
        answer = response.choices[0].message.content.strip()
        logger.info(f"Generated answer for {scheme_name}")
        return answer
    
    except Exception as e:
        logger.error(f"Live parser error: {e}")
        return f"I had trouble fetching details for {scheme_name}. Try the official website."
