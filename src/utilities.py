import requests
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Merriam-Webster API key
MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")

def get_definition(word):
    url = f"https://www.dictionaryapi.com/api/v3/references/learners/json/{word}?key={MERRIAM_WEBSTER_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an exception if the request failed
        log_request("definition", word)
    except requests.exceptions.RequestException as e:
        log_request("definition", word, success=False, error_message=str(e))
        return "No definition found due to an error.", None

    data = response.json()
    if not data:
        return "No definition found.", None

    result = ""
    audio_link = None
    for entry in data:
        # Using get() method to avoid KeyError
        if entry.get('fl'):
            result += f"\n\nPart of Speech: {entry['fl']}\n"
        if entry.get('shortdef'):
            result += "\nDefinitions:\n"
            for definition in entry['shortdef']:
                result += f"- {definition}\n"
        if entry.get('art') and entry['art'].get('artid'):
            result += f"\nIllustration: {entry['art']['artid']}\n"
        if entry.get('hwi') and entry['hwi'].get('prs'):            
            for pr in entry['hwi']['prs']:
                if pr.get('mw'):
                    result += f"- {pr['mw']}\n"
                if pr.get('sound') and pr['sound'].get('audio'):
                    audio_link = f"https://media.merriam-webster.com/soundc11/{word[0]}/{pr['sound']['audio']}.wav"
        if entry.get('def'):
            result += "\nUsage Examples:\n"
            for def_item in entry['def']:
                if def_item.get('sseq'):
                    for sseq_item in def_item['sseq']:
                        for item in sseq_item:
                            if isinstance(item, list) and len(item) > 1 and item[1].get('dt'):
                                for dt_item in item[1]['dt']:
                                    if isinstance(dt_item, list) and len(dt_item) > 1 and isinstance(dt_item[1], list):
                                        for vis_item in dt_item[1]:
                                            if isinstance(vis_item, dict) and vis_item.get('t'):
                                                result += f"- {vis_item['t']}\n"
    return result, audio_link

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
