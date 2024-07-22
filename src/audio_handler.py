import os
import requests
import logging

from src.database import update_audio_link, get_audio_path

# Directory to store downloaded audio files
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

def download_audio_file(url, word):
    local_filename = os.path.join(AUDIO_DIR, f"{word}.wav")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def get_audio_file(word, url):
    audio_path = get_audio_path(word)
    if not audio_path or not os.path.exists(audio_path):
        logging.info(f"Downloading audio file for word: {word}")
        audio_path = download_audio_file(url, word)
        update_audio_link(word, audio_path)
    return audio_path
