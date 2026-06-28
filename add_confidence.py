# Script to add confidence scoring to nodes.py
import re

with open(r'c:\Users\kusha\OneDrive\Desktop\welfare_2\agent\nodes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add confidence calculation to handle_faq
old_line = 'state["reply"] = reply or "I\'m here to help! Ask me about welfare schemes."'
new_line = '''state["reply"] = reply or "I'm here to help! Ask me about welfare schemes."
    state["confidence"] = calculate_confidence(state["message"], user_doc)'''

content = content.replace(old_line, new_line)

# Add the calculate_confidence function at the end
confidence_function = '''

def calculate_confidence(message: str, user_doc: dict) -> float:
    """Calculate confidence score for the response (0-100)."""
    confidence = 85.0  # Base confidence
    
    # Higher confidence for scheme-related questions
    scheme_keywords = ["scheme", "yojana", "benefit", "eligible", "pension", "scholarship", "kisan", "farmer", "student"]
    if any(kw in message.lower() for kw in scheme_keywords):
        confidence += 10
    
    # Lower confidence for very general or vague questions
    vague_keywords = ["something", "anything", "help", "what", "how"]
    if len(message.split()) < 3 or any(kw in message.lower() for kw in vague_keywords):
        confidence -= 15
    
    # Higher confidence if user has profile
    if user_doc and user_doc.get("name"):
        confidence += 5
    
    # Clamp between 0 and 100
    return max(0, min(100, confidence))
'''

content += confidence_function

with open(r'c:\Users\kusha\OneDrive\Desktop\welfare_2\agent\nodes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Confidence scoring added successfully")
