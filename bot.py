import os
import requests
import random
import time
import telebot
from telebot import types
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging

# 1Load environment variables from .env file
load_dotenv()

# Telegram bot token
TOKEN = os.getenv("TOKEN")

# Merriam-Webster API key
MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")

# Initialize the Telegram bot
bot = telebot.TeleBot(TOKEN, num_threads=10)

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Handler for the "/start" command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to the English learning bot!")

# Handler for the "/help" command
@bot.message_handler(commands=['help'])
def send_help(message):
    help_message = """
    Here are the available commands:
    - /start: Start the bot
    - /add [word]: Add a word to your local dictionary
    - /translate [word]: Get the translation of a word to Russian
    - /remove [word]: Remove a word from your local dictionary
    - /reminder: Get a random word reminder from your local dictionary
    - /help: Show this help message
    """
    bot.reply_to(message, help_message)

# Handler for processing user input
@bot.message_handler(func=lambda message: True)
def process_user_input(message):
    chat_id = message.chat.id
    text = message.text.lower()

    # Check if the user wants to add the word to the local dictionary
    if text.startswith('/add'):
        word = text.split(' ', 1)[1]
        local_dictionary[word] = None
        send_message_in_parts(chat_id, f"The word '{word}' has been added to your local dictionary.")
    
    # Check if the user wants to receive a translation
    elif text.startswith('/translate'):
        word = text.split(' ', 1)[1]
        translation = get_translation(word)
        if translation:
            send_message_in_parts(chat_id, f"The translation of '{word}' in Russian is '{translation}'.")
        else:
            send_message_in_parts(chat_id, f"Translation not found for the word '{word}'.")
    
    # Check if the user wants to remove a word from the local dictionary
    elif text.startswith('/remove'):
        word = text.split(' ', 1)[1]
        if word in local_dictionary:
            del local_dictionary[word]
            send_message_in_parts(chat_id, f"The word '{word}' has been removed from your local dictionary.")
        else:
            send_message_in_parts(chat_id, f"The word '{word}' is not present in your local dictionary.")
    
    # Check if the user wants a random word reminder
    elif text.startswith('/reminder'):
        random_word = random.choice(list(local_dictionary.keys()))
        local_dictionary[random_word] = time.time()
        send_message_in_parts(chat_id, f"Here's a random word from your local dictionary: {random_word}")
    
    # Check if the user wants the definition of a word
    else:
        definition = get_definition(text)
        send_message_in_parts(chat_id, definition, text)

def log_request(request_type, word, success=True, error_message=None):
    if success:
        logging.info(f"{request_type} request for word '{word}' was successful.")
    else:
        logging.error(f"{request_type} request for word '{word}' failed. Error: {error_message}")

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
            result += "\nPronunciations:\n"
            for pr in entry['hwi']['prs']:
                if pr.get('mw'):
                    result += f"- {pr['mw']}\n"
                if pr.get('sound') and pr['sound'].get('audio'):
                    result += f"Audio: https://media.merriam-webster.com/soundc11/{word[0]}/{pr['sound']['audio']}.wav\n"
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
    return result


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

# Function to send a message in parts to handle long messages
def send_message_in_parts(chat_id, text, word,  max_length=3800):

# Add the YouGlish link to the text
    text += f"\n\nYou can listen to the pronunciation of the word here: https://youglish.com/pronounce/{word}/english"
    text = format_text(text)

    if len(text) <= max_length:
        bot.send_message(chat_id, text, parse_mode='Markdown')
    else:
        parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
        for part in parts:
            bot.send_message(chat_id, part)

# Start the bot
if __name__ == "__main__":
    # Local dictionary to store user-added words
    local_dictionary = {}
    
    logging.info("Starting the bot...")
    bot.polling()