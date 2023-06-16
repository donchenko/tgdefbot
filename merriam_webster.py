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
        return "No definition found due to an error."
    data = response.json()
    if not data:
        return "No definition found."
    result = ""
    for entry in data:
        if 'fl' in entry:
            result += f"\n\nPart of Speech: {entry['fl']}\n"
        if 'shortdef' in entry:
            result += "\nDefinitions:\n"
            for definition in entry['shortdef']:
                result += f"- {definition}\n"
        if 'dros' in entry:
            result += "\nSpelling Suggestions:\n"
            for suggestion in entry['dros']:
                result += f"- {suggestion}\n"
        if 'art' in entry and 'artid' in entry['art']:
            result += f"\nIllustration: {entry['art']['artid']}\n"
        if 'hwi' in entry and 'prs' in entry['hwi']:
            result += "\nPronunciations:\n"
            for pr in entry['hwi']['prs']:
                if 'mw' in pr:
                    result += f"- {pr['mw']}\n"
                if 'sound' in pr and 'audio' in pr['sound']:
                    result += f"Audio: https://media.merriam-webster.com/soundc11/{word[0]}/{pr['sound']['audio']}.wav\n"
        if 'def' in entry:
            result += "\nUsage Examples:\n"
            for def_item in entry['def']:
                if 'sseq' in def_item:
                    for sseq_item in def_item['sseq']:
                        for item in sseq_item:
                            if isinstance(item, list) and len(item) > 1 and 'dt' in item[1]:
                                for dt_item in item[1]['dt']:
                                    if isinstance(dt_item, list) and len(dt_item) > 1 and isinstance(dt_item[1], list):
                                        for vis_item in dt_item[1]:
                                            if isinstance(vis_item, dict) and 't' in vis_item:
                                                result += f"- {vis_item['t']}\n"
    return result
