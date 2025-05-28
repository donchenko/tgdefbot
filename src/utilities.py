import requests
import logging
from dotenv import load_dotenv
import os
import re # Added for re.sub

# Load environment variables from .env file
load_dotenv()

# Merriam-Webster API key for accessing dictionary services.
MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")
# Logger instance for this module.
# Ensure logger is available. It might be configured in main.py and imported,
# or this module could be used standalone in scripts.
if 'logger' not in globals():
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers(): # Avoid adding handlers multiple times
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()] # Default to stream for scripts
        )


# This is the get_definition from the last read_files output
# I am keeping the version of get_definition and other functions as they were in the last read_files output,
# only modifying format_text and ensuring 'logger' is used.
def get_definition(word: str) -> tuple[str | None, str | None]:
    """
    Fetches the definition and related information for a given word using the Merriam-Webster Learner's Dictionary API.
    (This version is based on the last `read_files` output, assuming previous refactorings to it were not applied or lost)
    """
    url = f"https://www.dictionaryapi.com/api/v3/references/learners/json/{word}?key={MERRIAM_WEBSTER_API_KEY}"
    response = None # Initialize response
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        log_request("definition_api", word, success=True) 
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out for word '{word}' using Merriam-Webster API.")
        log_request("definition_api", word, success=False, error_message="Request timed out")
        return "Sorry, the request for definition timed out. Please try again.", None
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for word '{word}'. Error: {type(e).__name__}")
        log_request("definition_api", word, success=False, error_message=str(e))
        user_message = "Sorry, I couldn't fetch the definition due to a network or API issue."
        current_response = e.response if hasattr(e, 'response') else None # Check if response exists on exception
        if current_response is not None: # Check if current_response is not None
            if current_response.status_code == 404:
                 user_message = f"No definition found for '{word}'. Please check the spelling."
            elif current_response.status_code >= 500:
                 user_message = "The dictionary service is currently unavailable. Please try again later."
        return user_message, None

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as e_json:
        logger.error(f"Failed to decode JSON response for word '{word}'. Error: {e_json}.")
        log_request("definition_api_json_decode", word, success=False, error_message=f"JSONDecodeError: {e_json.msg}")
        return "Sorry, there was an issue processing the data from the dictionary service.", None

    if not data: # Handles empty list or None
        logger.info(f"No definition data found for '{word}' (empty data). API Response: {data}")
        return f"No definition found for '{word}'. Please ensure it's a valid English word.", None
    
    # Handle cases where data is a list of strings (suggestions)
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        suggestions = ", ".join(data)
        logger.info(f"API returned suggestions for '{word}': {suggestions}")
        return f"No definition found for '{word}'. Did you mean: {suggestions}?", None

    if not isinstance(data, list) or not isinstance(data[0], dict):
        logger.info(f"API response for '{word}' is not a list of definition objects. Response: {str(data)[:200]}")
        return f"No definition found for '{word}'. Unexpected data format from dictionary service.", None

    result = ""
    audio_link = None
    # Using the simpler parsing logic from the last `read_files` output for `get_definition`
    for entry in data:
        if not isinstance(entry, dict): continue # Skip if not a dictionary (e.g. if suggestions are mixed with other data)

        if entry.get('fl'): # Part of speech
            result += f"\n\nPart of Speech: {entry['fl']}\n"
        if entry.get('shortdef'): # Short definitions
            result += "\nDefinitions:\n"
            for definition_item in entry['shortdef']:
                result += f"- {definition_item}\n"
        
        # Pronunciation and audio link
        if entry.get('hwi') and entry['hwi'].get('prs'):            
            for pr in entry['hwi']['prs']:
                if pr.get('mw'): # Pronunciation text
                    result += f"\nPronunciation: {pr['mw']}\n" # Simplified output
                if not audio_link and pr.get('sound') and pr['sound'].get('audio'): # Take first audio
                    audio_file_name = pr['sound']['audio']
                    # Simplified subdir logic for now, matching common patterns
                    subdir = word[0] if word else ""
                    if audio_file_name.startswith("bix"): subdir = "bix"
                    elif audio_file_name.startswith("gg"): subdir = "gg"
                    elif audio_file_name.startswith("hom"): subdir = "hom"
                    elif audio_file_name.isdigit() or audio_file_name.startswith("_"): subdir = "number"
                    if subdir:
                         audio_link = f"https://media.merriam-webster.com/soundc11/{subdir}/{audio_file_name}.wav"
                    else:
                        logger.warning(f"Could not determine audio subdirectory for {audio_file_name} (word: {word})")
        
        # Usage Examples (simplified from the previous complex parsing)
        if entry.get('def'):
            for def_item in entry.get('def', []):
                if def_item.get('sseq'):
                    for sseq_item in def_item['sseq']:
                        for item_group in sseq_item:
                            if isinstance(item_group, list) and len(item_group) > 0:
                                content_item = item_group[1]
                                if content_item.get('dt'):
                                    for dt_element in content_item['dt']:
                                        if isinstance(dt_element, list) and len(dt_element) > 1 and dt_element[0] == "vis":
                                            if "Usage Examples:" not in result: result += "\nUsage Examples:\n"
                                            for vis_item in dt_element[1]:
                                                if isinstance(vis_item, dict) and vis_item.get('t'):
                                                    result += f"- {format_text(vis_item['t'])}\n" # Format example text
        if result: # If we got any content from this entry, break (take the first good entry)
            break
            
    if not result: # If loop completes and result is still empty
        logger.info(f"No processable content found in API data for '{word}'.")
        return f"No definition found for '{word}'.", None

    return result.strip(), audio_link


def format_text(text: str) -> str:
    """
    Formats text containing dictionary-specific tags (like {it} for italics, {phrase} for bold)
    into Markdown compatible formatting for Telegram.
    """
    if not text: return "" 
    
    text = text.replace('{it}', '_').replace('{/it}', '_')
    text = text.replace('{phrase}', '*').replace('{/phrase}', '*')
    text = text.replace('{b}', '*').replace('{/b}', '*')
    text = text.replace('{inf}', '').replace('{/inf}', '') 
    text = text.replace('{sup}', '').replace('{/sup}', '') 

    text = text.replace(' :', ':')
    text = re.sub(r'\s\s+', ' ', text) # Replace multiple spaces with a single space

    # Removed aggressive unpaired tag cleanup. Telegram might handle minor issues.
    # The focus is on converting known tags.
    return text.strip()

def get_translation(word: str) -> str | None:
    logger.info(f"Translation requested for word='{word}' (Not Implemented)")
    return None

def log_request(request_type: str, identifier: str, success: bool = True, error_message: str | None = None) -> None:
    if success:
        logger.info(f"Request Type: [{request_type}], Identifier: [{identifier}], Status: [Successful]")
    else:
        logger.error(f"Request Type: [{request_type}], Identifier: [{identifier}], Status: [Failed], Error: [{error_message or 'N/A'}]")
