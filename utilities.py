# utilities.py

import requests
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Merriam-Webster API key
MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")


# Function for formatting text from dictionary to telegram
def format_text(text):
    text = text.replace('{it}', '_').replace('{/it}', '_')
    text = text.replace('{phrase}', '*').replace('{/phrase}', '*')

    # Ensure all formatting symbols are paired
    if text.count('_') % 2 != 0:
        text = text.replace('_', '')  # Remove all unpaired '_'
    if text.count('*') % 2 != 0:
        text = text.replace('*', '')  # Remove all unpaired '*'

    return text

# Function to get translation from English to Russian
def get_translation(word):
    # Implement translation logic here or use an existing translation API
    return None

# Function for logging
def log_request(request_type, word, success=True, error_message=None):
    if success:
        logging.info(f"{request_type} request for word '{word}' was successful.")
    else:
        logging.error(f"{request_type} request for word '{word}' failed. Error: {error_message}")