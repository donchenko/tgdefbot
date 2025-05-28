import requests
import logging
from dotenv import load_dotenv
import os
import re 
from typing import Tuple, Optional, List, Dict, Any, Union

load_dotenv()

if 'logger' not in globals(): 
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers(): 
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")

def get_definition(word: str) -> Tuple[Optional[str], Optional[str]]:
    url = f"https://www.dictionaryapi.com/api/v3/references/learners/json/{word}?key={MERRIAM_WEBSTER_API_KEY}"
    response = None 
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
        current_response = e.response if hasattr(e, 'response') else None 
        if current_response is not None: 
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

    if not data: 
        logger.info(f"No definition data found for '{word}' (empty data). API Response: {data}")
        return f"No definition found for '{word}'. Please ensure it's a valid English word.", None
    
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        suggestions = ", ".join(data)
        logger.info(f"API returned suggestions for '{word}': {suggestions}")
        return f"No definition found for '{word}'. Did you mean: {suggestions}?", None

    if not isinstance(data, list) or not isinstance(data[0], dict):
        logger.info(f"API response for '{word}' is not a list of definition objects. Response: {str(data)[:200]}")
        return f"No definition found for '{word}'. Unexpected data format from dictionary service.", None

    result = ""
    audio_link = None
    for entry in data:
        if not isinstance(entry, dict): continue 

        if entry.get('fl'): 
            result += f"\n\nPart of Speech: {entry['fl']}\n"
        if entry.get('shortdef'): 
            result += "\nDefinitions:\n"
            for definition_item in entry['shortdef']:
                result += f"- {definition_item}\n"
        
        if entry.get('hwi') and entry['hwi'].get('prs'):            
            for pr in entry['hwi']['prs']:
                if pr.get('mw'): 
                    result += f"\nPronunciation: {pr['mw']}\n" 
                if not audio_link and pr.get('sound') and pr['sound'].get('audio'): 
                    audio_file_name = pr['sound']['audio']
                    subdir = word[0] if word else ""
                    if audio_file_name.startswith("bix"): subdir = "bix"
                    elif audio_file_name.startswith("gg"): subdir = "gg"
                    elif audio_file_name.startswith("hom"): subdir = "hom"
                    elif audio_file_name.isdigit() or audio_file_name.startswith("_"): subdir = "number"
                    if subdir:
                         audio_link = f"https://media.merriam-webster.com/soundc11/{subdir}/{audio_file_name}.wav"
                    else:
                        logger.warning(f"Could not determine audio subdirectory for {audio_file_name} (word: {word})")
        
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
                                                    result += f"- {format_text(vis_item['t'])}\n" 
        if result: 
            break
            
    if not result: 
        logger.info(f"No processable content found in API data for '{word}'.")
        return f"No definition found for '{word}'.", None

    return result.strip(), audio_link

def format_text(text: str) -> str:
    if not text: return "" 
    
    processed_text = text
    processed_text = processed_text.replace('{it}', '_').replace('{/it}', '_')
    processed_text = processed_text.replace('{phrase}', '*').replace('{/phrase}', '*')
    processed_text = processed_text.replace('{b}', '*').replace('{/b}', '*')
    processed_text = processed_text.replace('{inf}', '').replace('{/inf}', '') 
    processed_text = processed_text.replace('{sup}', '').replace('{/sup}', '') 

    processed_text = processed_text.replace(' :', ':')
    processed_text = re.sub(r'\s\s+', ' ', processed_text) 

    return processed_text.strip()

def get_translation(word: str) -> Optional[str]:
    logger.info(f"Translation requested for word='{word}' (Not Implemented)")
    return None

def log_request(request_type: str, identifier: str, success: bool = True, error_message: Optional[str] = None) -> None:
    if success:
        logger.info(f"Request Type: [{request_type}], Identifier: [{identifier}], Status: [Successful]")
    else:
        logger.error(f"Request Type: [{request_type}], Identifier: [{identifier}], Status: [Failed], Error: [{error_message or 'N/A'}]")
