import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('welfarebot.log')
    ]
)

logger = logging.getLogger(__name__)

def handle_groq_error(error, context=""):
    error_msg = str(error)
    logger.error(f"[GROQ ERROR] {context}: {error_msg}")
    logger.error(f"Error type: {type(error).__name__}")
    print(f"\n❌ GROQ ERROR in {context}: {error_msg}\n")
    return error_msg
